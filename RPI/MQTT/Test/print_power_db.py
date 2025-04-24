import sqlite3
import sys
import os # <-- Make sure os is imported

# --- Configuration ---
# Construct the path to power_data.db located two levels up (in the RPI folder)
SCRIPT_DIR = os.path.dirname(__file__)
DATABASE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'power_data.db'))
# --- End Configuration ---


def fetch_and_print_data(db_file):
    """Connects to the database, fetches all data, and prints it."""
    db_connection = None  # Initialize connection variable
    try:
        # Use the absolute path defined above
        print(f"Connecting to database: {db_file}")
        # Connect in read-only mode if possible (safer for just reading)
        # Note: URI mode might be needed for read-only on some systems/versions
        # db_connection = sqlite3.connect(f'file:{db_file}?mode=ro', uri=True)
        db_connection = sqlite3.connect(db_file)
        db_cursor = db_connection.cursor()
        print("Database connected.")

        # Fetch all data from the table
        print("\nFetching data from 'power_readings' table...")
        db_cursor.execute("SELECT id, reporter_device_id, source_device_id, timestamp_iso, timestamp_unix, power_watts, received_at FROM power_readings ORDER BY id")
        rows = db_cursor.fetchall()

        if not rows:
            print("The database table 'power_readings' is empty.")
            return

        # Print Header
        header = ["ID", "Reporter", "Source", "Timestamp (ISO/Raw)", "Timestamp (Unix)", "Power (W)", "Received At"]
        # Calculate column widths dynamically (optional, for better formatting)
        col_widths = [len(h) for h in header]
        for row in rows:
            for i, item in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(item) if item is not None else "NULL"))

        header_fmt = " | ".join([f"{h:<{col_widths[i]}}" for i, h in enumerate(header)])
        separator = "-+-".join(["-" * col_widths[i] for i in range(len(header))])

        print(header_fmt)
        print(separator)

        # Print Data Rows
        for row in rows:
            row_str = []
            for i, item in enumerate(row):
                # Format None as NULL, floats to 2 decimal places
                val_str = "NULL" if item is None else (f"{item:.2f}" if isinstance(item, float) else str(item))
                row_str.append(f"{val_str:<{col_widths[i]}}")
            print(" | ".join(row_str))

        print(f"\nTotal rows fetched: {len(rows)}")

    except sqlite3.OperationalError as e:
        # Handle case where DB file or table doesn't exist
        if "no such table" in str(e):
             print(f"Error: The table 'power_readings' does not exist in the database '{db_file}'.")
        elif "unable to open" in str(e):
             print(f"Error: Unable to open the database file '{db_file}'. Does it exist and have read permissions?")
        else:
             print(f"Database operational error: {e}")
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"An unexpected database error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        # Ensure the database connection is closed
        if db_connection:
            db_connection.close()
            print("\nDatabase connection closed.")

# --- Main Execution ---
if __name__ == "__main__":
    fetch_and_print_data(DATABASE_FILE)
