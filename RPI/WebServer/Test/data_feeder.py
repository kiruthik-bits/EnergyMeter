import sqlite3
import random
import os  # Import the os module for path manipulation
import time
from datetime import datetime, timezone

# --- Database File Path ---
# Construct the path to power_data.db located two levels up (in the RPI folder)
SCRIPT_DIR = os.path.dirname(__file__)
# Go up two levels from WebServer/Test/ to reach the RPI directory
DATABASE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'power_data.db'))
# --- End Database File Path ---

# --- Configuration ---
TABLE_NAME = 'power_readings'
DEVICES = ['Feeder_Device_A', 'Feeder_Device_B', 'Feeder_Device_C'] # Renamed to avoid confusion with populate_db
REPORTER_ID = 'DataFeederScript' # A specific reporter ID for this script
INSERT_INTERVAL_SECONDS = 5 # How often to insert new data (in seconds)
# --- End Configuration ---

def insert_random_data():
    """Connects to the database and inserts a new reading for each device."""
    conn = None
    try:
        # Connect to the correct database file
        conn = sqlite3.connect(DATABASE_FILE)
        # Enable WAL mode for consistency
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()

        records_to_insert = []
        now_utc = datetime.now(timezone.utc) # Use timezone-aware datetime

        for device_id in DEVICES:
            # Generate timestamp data
            timestamp_iso_str = now_utc.isoformat(timespec='seconds').replace('+00:00', 'Z') # ISO 8601 format with Z
            timestamp_unix_float = now_utc.timestamp() # Unix timestamp (float)

            # Generate random power reading
            power = round(random.uniform(10, 400), 2)  # Random power in watts

            # Prepare data tuple matching the power_readings schema
            records_to_insert.append((
                REPORTER_ID,
                device_id,          # Use device_id as source_device_id
                timestamp_iso_str,
                timestamp_unix_float,
                power               # Use power as power_watts
            ))

        # Use executemany for potentially faster bulk insertion
        c.executemany(f'''
            INSERT INTO {TABLE_NAME} (reporter_device_id, source_device_id, timestamp_iso, timestamp_unix, power_watts)
            VALUES (?, ?, ?, ?, ?)
        ''', records_to_insert)

        conn.commit()
        print(f"{datetime.now()}: Inserted {len(records_to_insert)} new records.")

    except sqlite3.Error as e:
        print(f"Database error during insert: {e}")
        if conn:
            conn.rollback() # Rollback changes on error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(f"Starting data feeder for database: {DATABASE_FILE}")
    print(f"Inserting data every {INSERT_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")
    try:
        while True:
            insert_random_data()
            time.sleep(INSERT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping data feeder.")

