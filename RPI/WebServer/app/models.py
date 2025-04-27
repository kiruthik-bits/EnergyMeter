# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/models.py
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple # Added type hints
from flask import current_app # Use current_app to access logger
import math

from .db import get_db # Import get_db from the db module

def get_latest_stats() -> Dict[str, Any]:
    """
    Fetches the latest power reading for each device and the total current power.
    Returns a dictionary containing device stats and total power.
    """
    conn = get_db()
    cursor = conn.cursor()
    result: Dict[str, Any] = {'Total': {'total_power': 0.0}}
    total_current_power = 0.0
    devices: List[str] = []

    try:
        # Get distinct device IDs that have reported data
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
        # Fetchall returns list of Row objects, extract the first element (device_id)
        devices = [row['source_device_id'] for row in cursor.fetchall()]

        for device_id in devices:
            # Get the most recent reading for each device based on timestamp_unix
            cursor.execute('''
                SELECT power_watts
                FROM power_readings
                WHERE source_device_id = ?
                ORDER BY timestamp_unix DESC, received_at DESC
                LIMIT 1
            ''', (device_id,))
            latest_reading = cursor.fetchone()

            if latest_reading and latest_reading['power_watts'] is not None:
                latest_power = round(float(latest_reading['power_watts']), 2)
                result[device_id] = {'latest': latest_power}
                total_current_power += latest_power
            else:
                 result[device_id] = {'latest': 0.0} # Default to float

        result['Total']['total_power'] = round(total_current_power, 2)

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_latest_stats: {e}")
        # Return a structured error in the result
        result = {'Total': {'total_power': 0.0}, 'error': f"Database error: {e}"}
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_latest_stats: {e}")
        result = {'Total': {'total_power': 0.0}, 'error': f"An unexpected error occurred: {e}"}
    # No finally block needed for closing connection, handled by teardown_appcontext

    return result

# --- Statistics Functions ---

def _get_time_range_timestamps(time_range_hours: int) -> Tuple[float, float]:
    """Helper function to get start and end Unix timestamps."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=time_range_hours)
    start_ts = start_time.timestamp()
    end_ts = end_time.timestamp()
    return start_ts, end_ts

def calculate_average_power(device_id: str, time_range_hours: int) -> Optional[float]:
    """Calculates the average power consumption for a device over a time range."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    average_power = None

    try:
        cursor.execute('''
            SELECT AVG(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND timestamp_unix BETWEEN ? AND ?
              AND power_watts IS NOT NULL
        ''', (device_id, start_ts, end_ts))
        result = cursor.fetchone()
        if result and result[0] is not None:
            average_power = round(float(result[0]), 2)
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error calculating average power for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error calculating average power for {device_id}: {e}")

    return average_power

def find_peak_usage(device_id: str, time_range_hours: int) -> Optional[Dict[str, Any]]:
    """Finds the highest power reading and its timestamp for a device over a time range."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    peak_data = None

    try:
        cursor.execute('''
            SELECT timestamp_unix, MAX(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND timestamp_unix BETWEEN ? AND ?
              AND power_watts IS NOT NULL
        ''', (device_id, start_ts, end_ts))
        result = cursor.fetchone()
        # Check if result is not None and both values are not None
        if result and result[0] is not None and result[1] is not None:
            peak_ts_unix = result[0]
            peak_power = round(float(result[1]), 2)
            # Convert peak timestamp to ISO format string
            dt_object = datetime.fromtimestamp(peak_ts_unix, tz=timezone.utc)
            peak_ts_iso = dt_object.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            peak_data = {
                'timestamp_unix': peak_ts_unix,
                'timestamp_iso': peak_ts_iso,
                'power': peak_power
            }
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error finding peak usage for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error finding peak usage for {device_id}: {e}")

    return peak_data

def calculate_total_energy_kwh(device_id: str, time_range_hours: int) -> Optional[float]:
    """
    Estimates the total energy consumed in kWh by integrating power over time.
    This is an approximation assuming power readings are taken at regular intervals.
    """
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    total_kwh = None

    try:
        # Fetch all relevant readings sorted by time
        cursor.execute('''
            SELECT timestamp_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND timestamp_unix BETWEEN ? AND ?
              AND timestamp_unix IS NOT NULL
              AND power_watts IS NOT NULL
            ORDER BY timestamp_unix ASC
        ''', (device_id, start_ts, end_ts))
        readings = cursor.fetchall()

        if len(readings) < 2:
            # Need at least two points to calculate energy over an interval
            return None

        total_watt_seconds = 0.0
        # Integrate using the trapezoidal rule (approximating area under the power curve)
        for i in range(len(readings) - 1):
            t1 = readings[i]['timestamp_unix']
            p1 = readings[i]['power_watts']
            t2 = readings[i+1]['timestamp_unix']
            p2 = readings[i+1]['power_watts']

            time_diff_seconds = t2 - t1
            avg_power_watts = (p1 + p2) / 2.0
            # Add energy for this interval (Watt-seconds or Joules)
            total_watt_seconds += avg_power_watts * time_diff_seconds

        # Convert Watt-seconds to kilowatt-hours (1 kWh = 3,600,000 Ws)
        total_kwh = round(total_watt_seconds / 3_600_000.0, 3)
        # Handle potential NaN if total_watt_seconds was NaN (unlikely here)
        if math.isnan(total_kwh):
             total_kwh = 0.0

    except sqlite3.Error as e:
        current_app.logger.error(f"DB error calculating total energy for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error calculating total energy for {device_id}: {e}")

    return total_kwh


def get_historical_data(device_id: str, time_range_hours: int) -> List[Dict[str, Any]]:
    """
    Fetches historical power readings for a specific device within a time range.
    Returns a list of dictionaries, each containing 'timestamp' (ISO string) and 'power'.
    """
    conn = get_db()
    cursor = conn.cursor()
    data: List[Dict[str, Any]] = []

    # Use timezone-aware datetime objects for calculations
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=time_range_hours)
    start_ts = start_time.timestamp() # Convert to Unix timestamp (float)
    end_ts = end_time.timestamp()     # Convert to Unix timestamp (float)

    try:
        cursor.execute('''
            SELECT timestamp_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND timestamp_unix BETWEEN ? AND ?
              AND timestamp_unix IS NOT NULL  -- Ensure timestamp is not NULL
              AND power_watts IS NOT NULL     -- Ensure power is not NULL
            ORDER BY timestamp_unix ASC
        ''', (device_id, start_ts, end_ts))

        for row in cursor.fetchall():
            # Convert Unix timestamp back to timezone-aware datetime, then to ISO format
            # Use UTC explicitly when creating datetime from timestamp
            dt_object = datetime.fromtimestamp(row['timestamp_unix'], tz=timezone.utc)
            # ISO 8601 format with 'Z' for UTC, suitable for JavaScript Date objects
            timestamp_str = dt_object.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            data.append({
                'timestamp': timestamp_str,
                'power': round(float(row['power_watts']), 2)
            })

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_historical_data for device {device_id}: {e}")
        # Return empty list in case of database error
        data = []
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_historical_data for device {device_id}: {e}")
        data = []

    return data

def get_distinct_devices() -> List[str]:
    """
    Fetches a list of distinct source_device_ids from the database.
    Returns a list of device ID strings.
    """
    conn = get_db()
    cursor = conn.cursor()
    devices: List[str] = []
    try:
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
        devices = [row['source_device_id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_distinct_devices: {e}")
        # Return empty list on error
        devices = []
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_distinct_devices: {e}")
        devices = []

    return devices
