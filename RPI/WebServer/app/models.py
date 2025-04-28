# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/models.py
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
import math

from .db import get_db

def get_latest_stats() -> Dict[str, Any]:
    """
    Fetches the latest power reading and its 'received_at' timestamp (as Unix epoch)
    for each device.
    """
    conn = get_db()
    cursor = conn.cursor()
    result: Dict[str, Any] = {'Total': {'total_power': 0.0}}
    total_current_power = 0.0
    devices: List[str] = []

    try:
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
        devices = [row['source_device_id'] for row in cursor.fetchall()]

        for device_id in devices:
            # Get the most recent reading based on received_at
            cursor.execute('''
                SELECT power_watts, unixepoch(received_at) as received_at_unix
                FROM power_readings
                WHERE source_device_id = ?
                  AND received_at IS NOT NULL -- Ensure received_at is not NULL
                  AND power_watts IS NOT NULL
                ORDER BY received_at DESC -- Order by received_at directly
                LIMIT 1
            ''', (device_id,))
            latest_reading = cursor.fetchone()

            if latest_reading:
                latest_power = round(float(latest_reading['power_watts']), 2)
                # Use received_at_unix instead of timestamp_unix
                latest_timestamp_unix = latest_reading['received_at_unix']
                result[device_id] = {
                    'latest': latest_power,
                    # Rename key for clarity in API response
                    'latest_timestamp_unix': latest_timestamp_unix
                }
                total_current_power += latest_power
            else:
                 result[device_id] = {
                     'latest': 0.0,
                     'latest_timestamp_unix': None # Indicate no timestamp
                 }

        result['Total']['total_power'] = round(total_current_power, 2)

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_latest_stats: {e}")
        result = {'Total': {'total_power': 0.0}, 'error': f"Database error: {e}"}
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_latest_stats: {e}")
        result = {'Total': {'total_power': 0.0}, 'error': f"An unexpected error occurred: {e}"}

    return result

# --- Statistics Functions ---

def _get_time_range_timestamps(time_range_hours: int) -> Tuple[float, float]:
    """Helper function to get start and end Unix timestamps for filtering."""
    # This remains the same as it defines the window based on current time
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=time_range_hours)
    start_ts = start_time.timestamp()
    end_ts = end_time.timestamp()
    return start_ts, end_ts

def calculate_average_power(device_id: str, time_range_hours: int) -> Optional[float]:
    """Calculates the average power consumption based on received_at time range."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    average_power = None

    try:
        # Filter using unixepoch(received_at)
        cursor.execute('''
            SELECT AVG(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND unixepoch(received_at) BETWEEN ? AND ?
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
    """Finds the highest power reading based on received_at time range."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    peak_data = None

    try:
        # Filter using unixepoch(received_at), find MAX power, get corresponding received_at_unix
        # Using a subquery or window function might be more robust for finding the exact timestamp
        # of the max value if multiple entries have the same max power.
        # Simpler approach: Find max power first, then find a timestamp for it.
        cursor.execute('''
            SELECT MAX(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND unixepoch(received_at) BETWEEN ? AND ?
              AND power_watts IS NOT NULL
        ''', (device_id, start_ts, end_ts))
        max_power_result = cursor.fetchone()

        if max_power_result and max_power_result[0] is not None:
            peak_power = round(float(max_power_result[0]), 2)
            # Now find one timestamp where this peak occurred within the range
            cursor.execute('''
                SELECT unixepoch(received_at) as peak_timestamp_unix
                FROM power_readings
                WHERE source_device_id = ?
                  AND unixepoch(received_at) BETWEEN ? AND ?
                  AND power_watts = ?
                ORDER BY received_at DESC -- Get the latest occurrence if multiple
                LIMIT 1
            ''', (device_id, start_ts, end_ts, peak_power))
            peak_ts_result = cursor.fetchone()

            if peak_ts_result and peak_ts_result['peak_timestamp_unix'] is not None:
                 peak_ts_unix = peak_ts_result['peak_timestamp_unix']
                 peak_data = {
                     # Rename key for clarity in API response
                     'timestamp_unix': peak_ts_unix,
                     'power': peak_power
                 }

    except sqlite3.Error as e:
        current_app.logger.error(f"DB error finding peak usage for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error finding peak usage for {device_id}: {e}")

    return peak_data

def calculate_total_energy_kwh(device_id: str, time_range_hours: int) -> Optional[float]:
    """
    Estimates total energy consumed (kWh) by integrating power over received_at time.
    """
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    total_kwh = None

    try:
        # Fetch unixepoch(received_at) and power_watts, ordered by received_at
        cursor.execute('''
            SELECT unixepoch(received_at) as ts_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND unixepoch(received_at) BETWEEN ? AND ?
              AND received_at IS NOT NULL
              AND power_watts IS NOT NULL
            ORDER BY received_at ASC -- Order by received_at directly
        ''', (device_id, start_ts, end_ts))
        readings = cursor.fetchall()

        if len(readings) < 2:
            return None

        total_watt_seconds = 0.0
        # Integrate using the trapezoidal rule with received_at timestamps (as Unix epoch)
        for i in range(len(readings) - 1):
            t1 = readings[i]['ts_unix']
            p1 = readings[i]['power_watts']
            t2 = readings[i+1]['ts_unix']
            p2 = readings[i+1]['power_watts']

            # Ensure timestamps are valid floats before calculation
            if t1 is None or t2 is None: continue

            time_diff_seconds = float(t2) - float(t1)
            # Avoid division by zero or negative time diff if data is weird
            if time_diff_seconds <= 0: continue

            avg_power_watts = (float(p1) + float(p2)) / 2.0
            total_watt_seconds += avg_power_watts * time_diff_seconds

        total_kwh = round(total_watt_seconds / 3_600_000.0, 3)
        if math.isnan(total_kwh):
             total_kwh = 0.0

    except sqlite3.Error as e:
        current_app.logger.error(f"DB error calculating total energy for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error calculating total energy for {device_id}: {e}")

    return total_kwh


def get_historical_data(device_id: str, time_range_hours: int) -> List[Dict[str, Any]]:
    """
    Fetches historical power readings, using received_at (as Unix epoch) for time.
    """
    conn = get_db()
    cursor = conn.cursor()
    data: List[Dict[str, Any]] = []
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)

    try:
        # Select unixepoch(received_at) and power_watts, filter by unixepoch(received_at)
        cursor.execute('''
            SELECT unixepoch(received_at) as received_at_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND unixepoch(received_at) BETWEEN ? AND ?
              AND received_at IS NOT NULL
              AND power_watts IS NOT NULL
            ORDER BY received_at ASC -- Order by received_at directly
        ''', (device_id, start_ts, end_ts))

        for row in cursor.fetchall():
            # Ensure timestamp is not None before adding
            if row['received_at_unix'] is not None:
                data.append({
                    # Rename key for clarity in API response
                    'timestamp': float(row['received_at_unix']),
                    'power': round(float(row['power_watts']), 2)
                })

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_historical_data for device {device_id}: {e}")
        data = []
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_historical_data for device {device_id}: {e}")
        data = []

    return data

def get_distinct_devices() -> List[str]:
    """Fetches a list of distinct source_device_ids."""
    # This function doesn't involve timestamps, so no change needed.
    conn = get_db()
    cursor = conn.cursor()
    devices: List[str] = []
    try:
        cursor.execute('SELECT DISTINCT source_device_id FROM power_readings ORDER BY source_device_id')
        devices = [row['source_device_id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_distinct_devices: {e}")
        devices = []
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_distinct_devices: {e}")
        devices = []

    return devices
