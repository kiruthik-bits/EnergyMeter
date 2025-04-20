import paho.mqtt.client as mqtt
import sqlite3
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

# --- Configuration ---
MQTT_BROKER_HOST = "localhost"  # Assumes Mosquitto is running on the RPi
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "sensors/power/dummy"  # Topic defined in dummy_data_send_mqtt.ino
MQTT_CLIENT_ID = "rpi-db-logger"

# --- MQTT Authentication ---
# Replace placeholders with your actual MQTT credentials if required by your broker.
MQTT_USER = "<YOUR_MQTT_USER>"      # MQTT Username (leave blank "" if none)
MQTT_PASSWORD = "<YOUR_MQTT_PASSWORD>"  # MQTT Password (leave blank "" if none)

DATABASE_FILE = "power_data.db"

# --- Database Schema ---
# Table Name: power_readings
# Columns:
#   id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique row ID.
#   reporter_device_id (TEXT NOT NULL):   ID of the ESP8266 reporting the data.
#   source_device_id (TEXT NOT NULL):     ID of the actual device/load being measured/simulated.
#   timestamp_iso (TEXT NOT NULL):        Timestamp string received from ESP8266 (ISO8601 or millis fallback).
#                                         Stored as TEXT to preserve original format and handle fallbacks.
#   timestamp_unix (REAL):                Timestamp converted to Unix epoch seconds (float).
#                                         NULL if original timestamp wasn't valid ISO8601.
#                                         Useful for sorting, indexing, and calculations. Indexed for performance.
#   power_watts (REAL NOT NULL):          The power reading in Watts.
#   received_at (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP): Timestamp when the RPi script received and processed the message.

# --- Global Variables ---
db_connection = None
db_cursor = None
mqtt_client = None

def setup_database():
    """Connects to the SQLite database and creates the table if it doesn't exist."""
    global db_connection, db_cursor
    try:
        print(f"Connecting to database: {DATABASE_FILE}")
        # Connect to the database. check_same_thread=False allows access from the MQTT callback thread.
        db_connection = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        # Enable Write-Ahead Logging (WAL) for better concurrency.
        db_connection.execute("PRAGMA journal_mode=WAL;")
        db_cursor = db_connection.cursor()
        print("Database connected.")

        # Create table if it doesn't exist (idempotent).
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
        # Create index on timestamp_unix for faster querying (idempotent).
        db_cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp_unix ON power_readings (timestamp_unix)
        ''')
        db_connection.commit()
        print("Database table 'power_readings' and index ensured.")
    except sqlite3.Error as e:
        print(f"Database error during setup: {e}")
        sys.exit(1) # Exit if DB setup fails.

def parse_iso_to_unix(iso_str):
    """Attempts to parse an ISO 8601 string (with 'Z' or timezone) to Unix epoch."""
    try:
        # Handle 'Z' for UTC explicitly for consistent parsing.
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'

        dt = datetime.fromisoformat(iso_str)
        # Ensure the datetime object is timezone-aware (assume UTC if naive).
        if dt.tzinfo is None:
             dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() # Returns float seconds since epoch.
    except (ValueError, TypeError):
        # Return None if parsing fails (e.g., not ISO format, or input is None).
        return None

# --- MQTT Callback Functions ---

def on_connect(client, userdata, flags, rc):
    """Callback executed when the client connects to the MQTT broker."""
    # Check connection result code (rc). 0 = success.
    if rc == 0:
        print(f"Connected to MQTT Broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        # Subscribe to the configured topic upon successful connection.
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    elif rc == 5:
        # Specific code for authentication failure.
        print(f"Failed to connect to MQTT Broker: Authentication Error (rc={rc}). Check username/password.")
    else:
        # General connection failure.
        print(f"Failed to connect to MQTT Broker, return code {rc}")

def on_message(client, userdata, msg):
    """Callback executed when a message is received on a subscribed topic."""
    print(f"Received message on topic '{msg.topic}'")
    try:
        # Decode payload from bytes to UTF-8 string.
        payload_str = msg.payload.decode("utf-8")
        # Parse the JSON string into a Python dictionary.
        data = json.loads(payload_str)

        # Extract expected fields using .get() to handle missing keys gracefully.
        reporter_id = data.get("reporterDeviceId")
        source_id = data.get("sourceDeviceId")
        timestamp_str = data.get("timestamp") # ISO string or millis() fallback from ESP.
        power = data.get("power")

        # --- Basic Data Validation ---
        # Check if all essential fields are present.
        if not all([reporter_id, source_id, timestamp_str is not None, power is not None]):
            print(f"  [WARN] Skipping message due to missing fields: {payload_str}")
            return
        # Validate the power value can be converted to a float.
        try:
            power_float = float(power)
        except (ValueError, TypeError):
             print(f"  [WARN] Skipping message due to invalid power value: {power}")
             return

        # --- Timestamp Conversion ---
        timestamp_unix_float = parse_iso_to_unix(timestamp_str)
        if timestamp_unix_float is None:
            # Log if the original timestamp wasn't a parseable ISO string.
            print(f"  [INFO] Timestamp '{timestamp_str}' is not valid ISO8601. Storing NULL for unix timestamp.")

        # --- Store data in SQLite using a transaction (ACID) ---
        try:
            if db_connection and db_cursor:
                # Begin Transaction for atomicity.
                db_cursor.execute("BEGIN TRANSACTION")

                # Insert data using parameterized query to prevent SQL injection.
                db_cursor.execute('''
                    INSERT INTO power_readings (reporter_device_id, source_device_id, timestamp_iso, timestamp_unix, power_watts)
                    VALUES (?, ?, ?, ?, ?)
                ''', (reporter_id, source_id, timestamp_str, timestamp_unix_float, power_float))

                # Commit Transaction for durability.
                db_connection.commit()
                print(f"  [OK] Stored: Rep={reporter_id}, Src={source_id}, TS={timestamp_str}, Pwr={power_float:.2f}")

            else:
                 # Should not happen if setup_database() succeeded.
                 print("  [ERROR] Database connection not available. Cannot store message.")
                 # Consider adding robust queuing/retry logic for production systems.

        except sqlite3.Error as e:
            # Handle database errors during insertion.
            print(f"  [ERROR] Failed to insert data into database: {e}")
            try:
                # Attempt to rollback the transaction to maintain consistency.
                if db_connection:
                    db_connection.rollback()
                    print("  [INFO] Transaction rolled back.")
            except sqlite3.Error as rb_e:
                print(f"  [ERROR] Failed to rollback transaction: {rb_e}")

    except json.JSONDecodeError:
        # Handle cases where the payload is not valid JSON.
        print(f"  [WARN] Received non-JSON message: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        # Catch any other unexpected errors during message processing.
        print(f"  [ERROR] An unexpected error occurred in on_message: {e}")

def on_disconnect(client, userdata, rc):
    """Callback executed when the client disconnects from the MQTT broker."""
    if rc != 0:
        # Log unexpected disconnections. Paho client usually handles automatic reconnections.
        print(f"Unexpected MQTT disconnection. Return code: {rc}. Attempting to reconnect...")
    else:
        print("MQTT client disconnected gracefully.")

# --- Signal Handling for Graceful Shutdown ---
def signal_handler(sig, frame):
    """Handles termination signals (SIGINT, SIGTERM) for graceful shutdown."""
    print("\nReceived termination signal. Shutting down...")
    global mqtt_client, db_connection

    # Disconnect MQTT client cleanly.
    if mqtt_client:
        try:
            mqtt_client.loop_stop() # Stop the background network loop.
            mqtt_client.disconnect() # Send DISCONNECT packet to broker.
            print("MQTT client disconnected.")
        except Exception as e:
            print(f"Error during MQTT disconnect: {e}")

    # Close database connection cleanly.
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
    # Register signal handlers for Ctrl+C (SIGINT) and kill/systemd stop (SIGTERM).
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize the database connection and schema.
    setup_database()

    # Initialize the MQTT client.
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    # Assign callback functions.
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    # Set MQTT username and password if provided in configuration.
    if MQTT_USER and MQTT_USER != "<YOUR_MQTT_USER>": # Check if placeholder is replaced
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
        print(f"Failed to connect to MQTT broker: {e}")
        if db_connection:
            db_connection.close() # Clean up DB connection before exiting.
        sys.exit(1) # Exit if initial connection fails.

    # Start the MQTT client's network loop in a background thread.
    # This handles receiving messages, keep-alives, and reconnections.
    mqtt_client.loop_start()

    # Keep the main thread alive until a termination signal is received.
    print("MQTT client started. Waiting for messages...")
    try:
        while True:
            # The main thread sleeps while the MQTT loop runs in the background.
            time.sleep(1)
            # Optional: Add periodic checks here if needed (e.g., MQTT connection status).
            # if not mqtt_client.is_connected():
            #    print("MQTT client appears disconnected...")

    except KeyboardInterrupt: # Primarily handled by SIGINT, but good as a fallback.
        print("KeyboardInterrupt received.")
        signal_handler(signal.SIGINT, None)
