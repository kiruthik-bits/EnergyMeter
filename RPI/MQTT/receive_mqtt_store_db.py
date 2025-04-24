# receive_mqtt_store_db.py
# Listens for MQTT messages containing power data (originally from a serial source via ESP8266)
# and stores the parsed data into an SQLite database.

import paho.mqtt.client as mqtt
import sqlite3
import json
import os # <-- Make sure os is imported
import signal
import sys
import time
from datetime import datetime, timezone

# --- Configuration ---
MQTT_BROKER_HOST = "localhost"  # IP address or hostname of the MQTT broker.
MQTT_BROKER_PORT = 1883         # Port for the MQTT broker (1883 is default for non-TLS).

# MQTT topic where the ESP8266 publishes the serial power data.
MQTT_TOPIC = "sensors/power/serial"
MQTT_CLIENT_ID = "rpi-db-logger-serial" # Unique identifier for this script when connecting to the broker.

# --- MQTT Authentication ---
# Replace placeholders with your actual MQTT credentials if required by your broker.
MQTT_USER = "<YOUR_MQTT_USER>"      # Username for MQTT broker authentication. Leave blank "" if none.
MQTT_PASSWORD = "<YOUR_MQTT_PASSWORD>"  # Password for MQTT broker authentication. Leave blank "" if none.

# --- Database File Path ---
# Construct the path to power_data.db located in the parent directory (RPI folder)
SCRIPT_DIR = os.path.dirname(__file__)
DATABASE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'power_data.db'))
# --- End Database File Path ---


# --- Database Schema Description ---
# Table Name: power_readings
# Purpose: Stores individual power readings received via MQTT.
# Columns:
#   id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for each database row.
#   reporter_device_id (TEXT NOT NULL):   Client ID of the ESP8266 that published the message.
#   source_device_id (TEXT NOT NULL):     Identifier of the device whose power is being measured (from serial data).
#   timestamp_iso (TEXT NOT NULL):        Timestamp string as received from the ESP8266 (expected ISO8601 format, e.g., "YYYY-MM-DDTHH:MM:SSZ", or millis() fallback).
#   timestamp_unix (REAL):                Timestamp converted to Unix epoch seconds (floating-point for sub-second precision if available). NULL if conversion from timestamp_iso fails. Indexed for efficient time-based queries.
#   power_watts (REAL NOT NULL):          The measured power value in Watts.
#   received_at (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP): Timestamp recorded by this script when the message was processed and inserted into the database.

# --- Global Variables ---
db_connection = None # Holds the database connection object.
db_cursor = None     # Holds the database cursor object.
mqtt_client = None   # Holds the MQTT client object.

def setup_database():
    """
    Initializes the connection to the SQLite database.
    Creates the 'power_readings' table and its index if they don't already exist.
    Enables Write-Ahead Logging (WAL) for better concurrency.
    """
    global db_connection, db_cursor
    try:
        # Use the absolute path defined above
        print(f"Connecting to database: {DATABASE_FILE}")
        # Connect to the SQLite database.
        # check_same_thread=False is necessary because the MQTT callbacks run in a separate thread.
        db_connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        # Enable Write-Ahead Logging (WAL) for better read/write concurrency.
        db_connection.execute("PRAGMA journal_mode=WAL;")
        db_cursor = db_connection.cursor()
        print("Database connected.")

        # Ensure the table exists. This is idempotent.
        db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS power_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_device_id TEXT NOT NULL,
                source_device_id TEXT NOT NULL,
                timestamp_iso TEXT NOT NULL,
                timestamp_unix REAL,
                power_watts REAL NOT NULL,
                received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Ensure the index on the Unix timestamp exists for faster queries. Idempotent.
        db_cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp_unix ON power_readings (timestamp_unix)
        ''')
        # Commit the table and index creation (if any occurred).
        db_connection.commit()
        print("Database table 'power_readings' and index ensured.")
    except sqlite3.Error as e:
        print(f"Database error during setup: {e}")
        sys.exit(1) # Exit if database setup fails critically.

def parse_iso_to_unix(iso_str):
    """
    Attempts to parse an ISO 8601 formatted timestamp string into a Unix epoch timestamp (float).
    Handles 'Z' suffix for UTC and assumes UTC if no timezone offset is provided.

    Args:
        iso_str (str): The timestamp string to parse.

    Returns:
        float: The Unix timestamp (seconds since epoch), or None if parsing fails.
    """
    try:
        # Replace 'Z' with the equivalent UTC offset '+00:00' for consistent parsing.
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'
        # Parse the ISO formatted string.
        dt = datetime.fromisoformat(iso_str)
        # If the parsed datetime object is naive (no timezone info), assume it's UTC.
        if dt.tzinfo is None:
             dt = dt.replace(tzinfo=timezone.utc)
        # Return the timestamp as seconds since the Unix epoch.
        return dt.timestamp()
    except (ValueError, TypeError):
        # Handle cases where the string is not a valid ISO format or is None.
        return None

# --- MQTT Callback Functions ---

def on_connect(client, userdata, flags, rc):
    """
    Callback executed when the MQTT client successfully connects to the broker.
    Subscribes to the specified MQTT topic upon connection.
    """
    if rc == 0: # Connection successful code
        print(f"Connected to MQTT Broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        # Subscribe to the topic upon successful connection.
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    elif rc == 5: # Connection refused - incorrect username/password
        print(f"Failed to connect to MQTT Broker: Authentication Error (rc={rc}). Check username/password.")
    else: # Other connection errors
        print(f"Failed to connect to MQTT Broker, return code {rc}")

def on_message(client, userdata, msg):
    """
    Callback executed when a message is received on a subscribed MQTT topic.
    Parses the JSON payload, validates data, and inserts it into the database.
    """
    print(f"Received message on topic '{msg.topic}'")
    try:
        # Decode the payload from bytes to a UTF-8 string.
        payload_str = msg.payload.decode("utf-8")
        # Parse the JSON string into a Python dictionary.
        data = json.loads(payload_str)

        # Extract expected fields from the JSON data.
        # Uses .get() to avoid KeyError if a field is missing, returning None instead.
        reporter_id = data.get("reporterDeviceId")
        source_id = data.get("sourceDeviceId") # The ID of the device measured via serial.
        timestamp_str = data.get("timestamp")  # The timestamp string from the ESP8266.
        power = data.get("power")              # The power reading.

        # --- Data Validation ---
        # Check if all essential fields were present in the JSON payload.
        if not all([reporter_id, source_id, timestamp_str is not None, power is not None]):
            print(f"  [WARN] Skipping message due to missing fields: {payload_str}")
            return
        # Try converting the power value to a float.
        try:
            power_float = float(power)
        except (ValueError, TypeError):
             print(f"  [WARN] Skipping message due to invalid power value type: {power}")
             return

        # --- Timestamp Conversion ---
        # Convert the received timestamp string to a Unix epoch float, if possible.
        timestamp_unix_float = parse_iso_to_unix(timestamp_str)
        if timestamp_unix_float is None:
            # Log if the timestamp wasn't in the expected ISO format. It will be stored as NULL in the DB.
            print(f"  [INFO] Timestamp '{timestamp_str}' is not valid ISO8601. Storing NULL for unix timestamp.")

        # --- Database Insertion ---
        # Use a database transaction for atomic writes. Ensures data integrity.
        try:
            if db_connection and db_cursor:
                # Begin the transaction.
                db_cursor.execute("BEGIN TRANSACTION")
                # Execute the INSERT statement with parameterized query to prevent SQL injection.
                db_cursor.execute('''
                    INSERT INTO power_readings (reporter_device_id, source_device_id, timestamp_iso, timestamp_unix, power_watts)
                    VALUES (?, ?, ?, ?, ?)
                ''', (reporter_id, source_id, timestamp_str, timestamp_unix_float, power_float))
                # Commit the transaction to make the changes permanent.
                db_connection.commit()
                print(f"  [OK] Stored: Rep={reporter_id}, Src={source_id}, TS={timestamp_str}, Pwr={power_float:.2f}")
            else:
                 # This should ideally not happen if setup was successful.
                 print("  [ERROR] Database connection not available. Cannot store message.")
                 # Consider adding queuing/retry logic here for robustness.
        except sqlite3.Error as e:
            # Handle potential database errors during insertion (e.g., disk full).
            print(f"  [ERROR] Failed to insert data into database: {e}")
            try:
                # Attempt to rollback the transaction to leave the DB in a consistent state.
                if db_connection:
                    db_connection.rollback()
                    print("  [INFO] Transaction rolled back.")
            except sqlite3.Error as rb_e:
                # Log if rollback fails (rare, but possible).
                print(f"  [ERROR] Failed to rollback transaction: {rb_e}")

    except json.JSONDecodeError:
        # Handle cases where the payload is not valid JSON.
        print(f"  [WARN] Received non-JSON message: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        # Catch any other unexpected errors during message processing.
        print(f"  [ERROR] An unexpected error occurred in on_message: {e}")

def on_disconnect(client, userdata, rc):
    """
    Callback executed when the MQTT client disconnects from the broker.
    """
    if rc != 0:
        # Log unexpected disconnections. The Paho client usually attempts auto-reconnect.
        print(f"Unexpected MQTT disconnection. Return code: {rc}. Attempting to reconnect...")
    else:
        # Log graceful disconnections.
        print("MQTT client disconnected gracefully.")

# --- Signal Handling for Graceful Shutdown ---
def signal_handler(sig, frame):
    """
    Handles termination signals (SIGINT, SIGTERM) to ensure graceful shutdown.
    Disconnects the MQTT client and closes the database connection.
    """
    print("\nReceived termination signal. Shutting down...")
    global mqtt_client, db_connection

    # Stop the MQTT client loop and disconnect.
    if mqtt_client:
        try:
            mqtt_client.loop_stop() # Stops the background network thread.
            mqtt_client.disconnect() # Sends the MQTT DISCONNECT packet.
            print("MQTT client disconnected.")
        except Exception as e:
            print(f"Error during MQTT disconnect: {e}")

    # Close the database connection.
    if db_connection:
        try:
            db_connection.close()
            print("Database connection closed.")
        except sqlite3.Error as e:
            print(f"Error closing database: {e}")

    print("Shutdown complete.")
    sys.exit(0) # Exit the script cleanly.

# --- Main Execution Block ---
if __name__ == "__main__":
    # Register signal handlers for graceful shutdown on Ctrl+C (SIGINT) or `kill` (SIGTERM).
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize the database connection and schema.
    setup_database()

    # Initialize the MQTT client with the specified client ID.
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    # Assign the callback functions.
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    # Set MQTT username and password if provided and not placeholders.
    if MQTT_USER and MQTT_USER != "<YOUR_MQTT_USER>":
        print(f"Setting MQTT username: {MQTT_USER}")
        if MQTT_PASSWORD and MQTT_PASSWORD != "<YOUR_MQTT_PASSWORD>":
            mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        else:
             mqtt_client.username_pw_set(MQTT_USER) # Username only
    else:
        print("Connecting to MQTT broker without authentication.")

    # Attempt to connect to the MQTT broker.
    try:
        print(f"Connecting to MQTT broker {MQTT_BROKER_HOST}...")
        # Connect with a 60-second keep-alive interval.
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    except Exception as e:
        # Handle connection errors (e.g., broker unreachable).
        print(f"Failed to connect to MQTT broker: {e}")
        if db_connection: # Ensure DB connection is closed if MQTT fails at startup.
            db_connection.close()
        sys.exit(1) # Exit if initial connection fails.

    # Start the MQTT client's network loop in a background thread.
    # This handles reconnects, keep-alives, and message dispatching.
    mqtt_client.loop_start()

    print("MQTT client started. Waiting for messages on topic '{}'...".format(MQTT_TOPIC))
    # Keep the main thread alive indefinitely, relying on the signal handler for shutdown.
    try:
        while True:
            # The main thread doesn't need to do much here as MQTT runs in the background.
            time.sleep(1)
            # Optional: Add checks here, e.g., monitor MQTT connection status if needed.
            # if not mqtt_client.is_connected():
            #     print("MQTT client appears disconnected...")
    except KeyboardInterrupt:
        # This is caught if Ctrl+C is pressed, but the signal handler should take precedence.
        print("KeyboardInterrupt received (should be handled by signal handler).")
        signal_handler(signal.SIGINT, None) # Explicitly call handler just in case.

