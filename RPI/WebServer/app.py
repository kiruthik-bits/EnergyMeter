# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app.py
from flask import Flask, render_template, jsonify, request # Added request
import sqlite3
import os
import time # Added for time calculations
from datetime import datetime, timedelta # Added for time calculations

app = Flask(__name__)

# Use the correct database file populated by the MQTT script
DATABASE = 'power_data.db'

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    # Ensure the path is relative to the app's directory, not the CWD
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', DATABASE)
    try:
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) # Added detect_types
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database at {db_path}: {e}")
        # In a real app, you might want to raise this or handle it differently
        return None


def get_latest_stats():
    """
    Fetches the latest power reading for each device and the total current power.
    """
    conn = get_db()
    if not conn:
        return {'Total': {'total_power': 0}, 'error': 'Database connection failed'}

    cursor = conn.cursor()
    result = {}
    total_current_power = 0

    try:
        # Get distinct device IDs that have reported data
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
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
                }
                total_current_power += latest_power
            else:
                 result[device_id] = {'latest': 0}

        result['Total'] = {
            'total_power': round(total_current_power, 2)
        }

    except sqlite3.Error as e:
        print(f"Database error in get_latest_stats: {e}")
        result = {'Total': {'total_power': 0}, 'error': str(e)}
    finally:
        if conn:
            conn.close()

    return result

# --- New Function for Historical Data ---
def get_historical_data(device_id, time_range_hours):
    """
    Fetches historical power readings for a specific device within a time range.
    """
    conn = get_db()
    if not conn:
        return [] # Return empty list on connection error

    cursor = conn.cursor()
    data = []
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=time_range_hours)
    # Convert to Unix timestamps (assuming timestamp_unix stores Unix timestamps)
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())

    try:
        # Fetch timestamp and power, ordering by timestamp
        # Using timestamp_unix as the primary time source
        cursor.execute('''
            SELECT timestamp_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND timestamp_unix BETWEEN ? AND ?
            ORDER BY timestamp_unix ASC
        ''', (device_id, start_ts, end_ts))

        # Convert rows to a list of dictionaries for easier JSON serialization
        # Also convert Unix timestamp back to ISO format string for Chart.js
        for row in cursor.fetchall():
             # Check if timestamp_unix is not None before converting
            if row['timestamp_unix'] is not None:
                dt_object = datetime.fromtimestamp(row['timestamp_unix'])
                # Format for Chart.js time scale (ISO 8601)
                timestamp_str = dt_object.isoformat()
                data.append({
                    'timestamp': timestamp_str,
                    'power': round(row['power_watts'], 2)
                })
            # else: # Optionally handle rows where timestamp_unix is NULL
            #    print(f"Skipping row with NULL timestamp_unix for device {device_id}")


    except sqlite3.Error as e:
        print(f"Database error in get_historical_data for device {device_id}: {e}")
        # Return empty list in case of error
        data = []
    finally:
        if conn:
            conn.close()

    return data

# --- New Route for Historical Page ---
@app.route('/history')
def history():
    """Serves the historical data page."""
    # Check if the database file exists before rendering
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', DATABASE)
    if not os.path.exists(db_path):
         return "Error: Database file 'power_data.db' not found.", 500
    return render_template('history.html')

# --- New API Endpoint for Device List ---
@app.route('/api/devices')
def get_devices():
    """Provides a list of distinct device IDs."""
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()
    devices = []
    try:
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
        devices = [row['source_device_id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error in get_devices: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
    return jsonify(devices)


# --- New API Endpoint for Historical Data ---
@app.route('/api/historical_data')
def api_historical_data():
    """Provides historical power data as JSON based on query parameters."""
    device_id = request.args.get('device_id')
    # Default to 1 hour if not specified or invalid
    try:
        time_range_hours = int(request.args.get('hours', 1))
    except (ValueError, TypeError):
        time_range_hours = 1

    if not device_id:
        return jsonify({"error": "Missing 'device_id' parameter"}), 400

    # Add validation for time_range_hours if needed (e.g., max value)
    if time_range_hours <= 0:
         return jsonify({"error": "Invalid 'hours' parameter"}), 400

    data = get_historical_data(device_id, time_range_hours)
    return jsonify(data)


@app.route('/data')
def data():
    """Provides the latest power data as JSON."""
    stats = get_latest_stats()
    return jsonify(stats)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    # Check if the database file exists before rendering
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', DATABASE)
    if not os.path.exists(db_path):
         return "Error: Database file 'power_data.db' not found.", 500
    # Pass device list to the main dashboard as well, if needed there
    return render_template('index.html')

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', DATABASE)
    print(f"Looking for database at: {db_path}")
    if not os.path.exists(db_path):
        print("WARNING: Database file not found. Please ensure the MQTT script is running and creating the database.")
    # Use host='0.0.0.0' to make the server accessible on your network
    app.run(host='0.0.0.0', port=5000, debug=True) # Keep debug=True for development
