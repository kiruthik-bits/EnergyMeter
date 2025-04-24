import sqlite3
import random
import os # Import os module
from datetime import datetime, timedelta, timezone

# --- Database File Path ---
# Construct the path to power_data.db located two levels up (in the RPI folder)
SCRIPT_DIR = os.path.dirname(__file__)
# Go up two levels from WebServer/Test/ to reach the RPI directory
DATABASE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'power_data.db'))
# --- End Database File Path ---


# --- Configuration ---
TABLE_NAME = 'power_readings'
DEVICES = ['Simulated_Device_A', 'Simulated_Device_B', 'Simulated_Device_C']
REPORTER_ID = 'ESP_Populator_Script' # A dummy reporter ID for these entries
NUM_RECORDS_PER_DEVICE = 50
# --- End Configuration ---

def populate_database():
    """Connects to the database, ensures the table exists, and inserts dummy data."""
    conn = None
    try:
        print(f"Connecting to database: {DATABASE_FILE}")
        conn = sqlite3.connect(DATABASE_FILE)
        # Enable WAL mode, consistent with the MQTT logger script
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()
        print("Database connected.")

        # Ensure the table exists with the correct schema (idempotent)
        # Matches the schema in receive_mqtt_store_db.py
        print(f"Ensuring table '{TABLE_NAME}' exists...")
        c.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_device_id TEXT NOT NULL,
                source_device_id TEXT NOT NULL,
                timestamp_iso TEXT NOT NULL,
                timestamp_unix REAL,
                power_watts REAL NOT NULL,
                received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Ensure the index exists (idempotent)
        c.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_timestamp_unix ON {TABLE_NAME} (timestamp_unix)
        ''')
        conn.commit()
        print(f"Table '{TABLE_NAME}' and index ensured.")

        # Insert dummy records
        print(f"Inserting {NUM_RECORDS_PER_DEVICE} dummy records per device...")
        now_utc = datetime.now(timezone.utc) # Use timezone-aware datetime

        records_to_insert = []
        for device_id in DEVICES:
            for i in range(NUM_RECORDS_PER_DEVICE):
                # Generate timestamp going back in time
                timestamp_dt = now_utc - timedelta(minutes=i * 15) # Increase time gap for clarity
                timestamp_iso_str = timestamp_dt.isoformat(timespec='seconds').replace('+00:00', 'Z') # ISO 8601 format with Z
                timestamp_unix_float = timestamp_dt.timestamp() # Unix timestamp (float)

                # Generate random power reading
                power = round(random.uniform(20, 350), 2)  # Random power in watts

                records_to_insert.append((
                    REPORTER_ID,
                    device_id,
                    timestamp_iso_str,
                    timestamp_unix_float,
                    power
                ))

        # Use executemany for potentially faster bulk insertion
        c.executemany(f'''
            INSERT INTO {TABLE_NAME} (reporter_device_id, source_device_id, timestamp_iso, timestamp_unix, power_watts)
            VALUES (?, ?, ?, ?, ?)
        ''', records_to_insert)

        conn.commit()
        print(f"Successfully inserted {len(records_to_insert)} records.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback() # Rollback changes on error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    populate_database()

