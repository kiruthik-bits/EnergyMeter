# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app.py
from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)

# Use the correct database file populated by the MQTT script
DATABASE = 'power_data.db' # Changed from 'energy.db'

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', DATABASE) # Adjust path relative to app.py
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def get_latest_stats():
    """
    Fetches the latest power reading for each device and the total current power.
    """
    conn = get_db()
    cursor = conn.cursor()
    result = {}
    total_current_power = 0

    try:
        # Get distinct device IDs that have reported data
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings')
        devices = [row['source_device_id'] for row in cursor.fetchall()]

        for device_id in devices:
            # Get the most recent reading for each device based on timestamp_unix
            # Fallback to received_at if timestamp_unix is NULL often
            cursor.execute('''
                SELECT power_watts
                FROM power_readings
                WHERE source_device_id = ?
                ORDER BY timestamp_unix DESC, received_at DESC
                LIMIT 1
            ''', (device_id,))
            latest_reading = cursor.fetchone()

            if latest_reading:
                latest_power = round(latest_reading['power_watts'], 2)
                result[device_id] = {
                    'latest': latest_power
                    # You could add average/peak calculations here if needed,
                    # querying more data (e.g., last N readings or time window)
                }
                total_current_power += latest_power
            else:
                # Handle case where a device ID exists but somehow has no readings (unlikely)
                 result[device_id] = {'latest': 0}

        # Add the total current power consumption (sum of latest readings)
        result['Total'] = {
            'total_power': round(total_current_power, 2)
            # Note: This is instantaneous total power, not energy (kWh) over time.
            # Calculating energy requires integrating power over time intervals.
        }

    except sqlite3.Error as e:
        print(f"Database error in get_latest_stats: {e}")
        # Return empty or default data in case of error
        result = {'Total': {'total_power': 0}}
    finally:
        conn.close()

    return result

@app.route('/data')
def data():
    """Provides the latest power data as JSON."""
    stats = get_latest_stats()
    return jsonify(stats)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    # Check if the database file exists before rendering
    db_path = os.path.join(os.path.dirname(__file__), '..', DATABASE)
    if not os.path.exists(db_path):
         # Optionally, render an error page or message
         return "Error: Database file 'power_data.db' not found.", 500
    return render_template('index.html')

if __name__ == '__main__':
    # Make sure the database path is correct relative to where app.py is run
    print(f"Looking for database at: {os.path.join(os.path.dirname(__file__), '..', DATABASE)}")
    # Use host='0.0.0.0' to make the server accessible on your network
    app.run(host='0.0.0.0', port=5000, debug=True)
