# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/Test/populate_week.py
import sqlite3
import random
import os
from datetime import datetime, timedelta, timezone

# --- Database File Path ---
# Construct the path to power_data.db located two levels up (in the RPI folder)
SCRIPT_DIR = os.path.dirname(__file__)
# Go up two levels from WebServer/Test/ to reach the RPI directory
DATABASE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'power_data.db'))
# --- End Database File Path ---


# --- Configuration ---
TABLE_NAME = 'power_readings'
DEVICES = ['Weekly_Device_X', 'Weekly_Device_Y'] # Example devices
REPORTER_ID = 'ESP_Weekly_Populator' # A dummy reporter ID for these entries
DAYS_TO_POPULATE = 7
# Define the interval between data points (e.g., every 15 minutes)
DATA_INTERVAL_MINUTES = 15
# --- End Configuration ---

def populate_weekly_data():
    """Connects to the database, ensures the table exists, and inserts data for the specified number of days."""
    conn = None
    try:
        print(f"Connecting to database: {DATABASE_FILE}")
        conn = sqlite3.connect(DATABASE_FILE)
        # Enable WAL mode, consistent with other scripts
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()
        print("Database connected.")

        # Ensure the table exists with the correct schema (idempotent)
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

        # Calculate the total number of intervals in the specified period
        total_intervals = (DAYS_TO_POPULATE * 24 * 60) // DATA_INTERVAL_MINUTES

        print(f"Preparing to insert data for {DAYS_TO_POPULATE} days ({total_intervals} intervals per device)...")
        now_utc = datetime.now(timezone.utc) # Use timezone-aware datetime

        records_to_insert = []
        for device_id in DEVICES:
            print(f"  Generating data for device: {device_id}")
            for i in range(total_intervals):
                # Generate timestamp going back in time
                timestamp_dt = now_utc - timedelta(minutes=i * DATA_INTERVAL_MINUTES)
                timestamp_iso_str = timestamp_dt.isoformat(timespec='seconds').replace('+00:00', 'Z') # ISO 8601 format with Z
                timestamp_unix_float = timestamp_dt.timestamp() # Unix timestamp (float)

                # Generate random power reading (adjust range as needed)
                # Simulate some variation, maybe lower at night?
                hour_of_day = timestamp_dt.hour
                if 6 <= hour_of_day < 22: # Daytime
                    power = round(random.uniform(50, 450), 2)
                else: # Nighttime
                    power = round(random.uniform(10, 100), 2)

                records_to_insert.append((
                    REPORTER_ID,
                    device_id,
                    timestamp_iso_str,
                    timestamp_unix_float,
                    power
                ))

        print(f"Inserting {len(records_to_insert)} records...")
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
    print("Starting weekly data population script...")
    populate_weekly_data()
    print("Weekly data population finished.")
