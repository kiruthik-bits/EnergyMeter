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
    for each device, using strftime for compatibility.
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
            # Use CAST(strftime('%s', ...) AS REAL) instead of unixepoch()
            cursor.execute('''
                SELECT power_watts, CAST(strftime('%s', received_at) AS REAL) as received_at_unix
                FROM power_readings
                WHERE source_device_id = ?
                  AND received_at IS NOT NULL
                  AND power_watts IS NOT NULL
                ORDER BY received_at DESC
                LIMIT 1
            ''', (device_id,))
            latest_reading = cursor.fetchone()

            if latest_reading and latest_reading['received_at_unix'] is not None: # Check if timestamp conversion worked
                latest_power = round(float(latest_reading['power_watts']), 2)
                latest_timestamp_unix = float(latest_reading['received_at_unix']) # Ensure it's float
                result[device_id] = {
                    'latest': latest_power,
                    'latest_timestamp_unix': latest_timestamp_unix
                }
                total_current_power += latest_power
            else:
                 result[device_id] = {
                     'latest': 0.0,
                     'latest_timestamp_unix': None
                 }

        result['Total']['total_power'] = round(total_current_power, 2)

    except sqlite3.Error as e:
        # Log the specific error
        current_app.logger.error(f"Database error in get_latest_stats: {e}")
        result = {'Total': {'total_power': 0.0}, 'error': f"Database error: {e}"}
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_latest_stats: {e}", exc_info=True) # Add exc_info for more details
        result = {'Total': {'total_power': 0.0}, 'error': f"An unexpected error occurred: {e}"}

    return result

# --- Statistics Functions ---

def _get_time_range_timestamps(time_range_hours: int) -> Tuple[float, float]:
    """Helper function to get start and end Unix timestamps for filtering."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=time_range_hours)
    start_ts = start_time.timestamp()
    end_ts = end_time.timestamp()
    return start_ts, end_ts

def calculate_average_power(device_id: str, time_range_hours: int) -> Optional[float]:
    """Calculates the average power consumption based on received_at time range, using strftime."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    average_power = None

    try:
        # Filter using strftime('%s', received_at)
        cursor.execute('''
            SELECT AVG(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND strftime('%s', received_at) BETWEEN ? AND ?
              AND power_watts IS NOT NULL
              AND received_at IS NOT NULL -- Added check for received_at
        ''', (device_id, start_ts, end_ts))
        result = cursor.fetchone()
        if result and result[0] is not None:
            average_power = round(float(result[0]), 2)
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error calculating average power for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error calculating average power for {device_id}: {e}", exc_info=True)

    return average_power

def find_peak_usage(device_id: str, time_range_hours: int) -> Optional[Dict[str, Any]]:
    """Finds the highest power reading based on received_at time range, using strftime."""
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    peak_data = None

    try:
        # Find max power first, filtering with strftime
        cursor.execute('''
            SELECT MAX(power_watts)
            FROM power_readings
            WHERE source_device_id = ?
              AND strftime('%s', received_at) BETWEEN ? AND ?
              AND power_watts IS NOT NULL
              AND received_at IS NOT NULL -- Added check for received_at
        ''', (device_id, start_ts, end_ts))
        max_power_result = cursor.fetchone()

        if max_power_result and max_power_result[0] is not None:
            peak_power = round(float(max_power_result[0]), 2)
            # Now find one timestamp where this peak occurred within the range
            # Use CAST(strftime('%s', ...) AS REAL)
            cursor.execute('''
                SELECT CAST(strftime('%s', received_at) AS REAL) as peak_timestamp_unix
                FROM power_readings
                WHERE source_device_id = ?
                  AND strftime('%s', received_at) BETWEEN ? AND ?
                  AND power_watts = ?
                  AND received_at IS NOT NULL -- Added check for received_at
                ORDER BY received_at DESC
                LIMIT 1
            ''', (device_id, start_ts, end_ts, peak_power))
            peak_ts_result = cursor.fetchone()

            if peak_ts_result and peak_ts_result['peak_timestamp_unix'] is not None:
                 peak_ts_unix = float(peak_ts_result['peak_timestamp_unix']) # Ensure float
                 peak_data = {
                     'timestamp_unix': peak_ts_unix,
                     'power': peak_power
                 }

    except sqlite3.Error as e:
        current_app.logger.error(f"DB error finding peak usage for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error finding peak usage for {device_id}: {e}", exc_info=True)

    return peak_data

def calculate_total_energy_kwh(device_id: str, time_range_hours: int) -> Optional[float]:
    """
    Estimates total energy consumed (kWh) by integrating power over received_at time, using strftime.
    """
    conn = get_db()
    cursor = conn.cursor()
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)
    total_kwh = None

    try:
        # Fetch CAST(strftime('%s', ...) AS REAL) and power_watts, ordered by received_at
        cursor.execute('''
            SELECT CAST(strftime('%s', received_at) AS REAL) as ts_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND strftime('%s', received_at) BETWEEN ? AND ?
              AND received_at IS NOT NULL
              AND power_watts IS NOT NULL
            ORDER BY received_at ASC
        ''', (device_id, start_ts, end_ts))
        readings = cursor.fetchall()

        if len(readings) < 2:
            return None

        total_watt_seconds = 0.0
        # Integrate using the trapezoidal rule with received_at timestamps (as Unix epoch)
        for i in range(len(readings) - 1):
            # Ensure timestamps and power values are valid floats before calculation
            try:
                t1 = float(readings[i]['ts_unix'])
                p1 = float(readings[i]['power_watts'])
                t2 = float(readings[i+1]['ts_unix'])
                p2 = float(readings[i+1]['power_watts'])
            except (TypeError, ValueError):
                current_app.logger.warning(f"Skipping interval due to invalid data: {readings[i]} or {readings[i+1]}")
                continue # Skip this interval if conversion fails

            time_diff_seconds = t2 - t1
            # Avoid division by zero or negative time diff if data is weird
            if time_diff_seconds <= 0:
                current_app.logger.warning(f"Skipping interval due to non-positive time difference: {time_diff_seconds}s")
                continue

            avg_power_watts = (p1 + p2) / 2.0
            total_watt_seconds += avg_power_watts * time_diff_seconds

        # Convert Watt-seconds to kWh
        total_kwh = round(total_watt_seconds / 3_600_000.0, 3)
        if math.isnan(total_kwh): # Check for NaN resulting from potential issues
             current_app.logger.warning(f"Calculated NaN for total energy for {device_id}. Returning 0.0.")
             total_kwh = 0.0

    except sqlite3.Error as e:
        current_app.logger.error(f"DB error calculating total energy for {device_id}: {e}")
    except Exception as e:
        current_app.logger.error(f"Error calculating total energy for {device_id}: {e}", exc_info=True)

    return total_kwh


def get_historical_data(device_id: str, time_range_hours: int) -> List[Dict[str, Any]]:
    """
    Fetches historical power readings, using received_at (as Unix epoch via strftime) for time.
    """
    conn = get_db()
    cursor = conn.cursor()
    data: List[Dict[str, Any]] = []
    start_ts, end_ts = _get_time_range_timestamps(time_range_hours)

    try:
        # Select CAST(strftime('%s', ...) AS REAL) and power_watts, filter by strftime('%s', received_at)
        cursor.execute('''
            SELECT CAST(strftime('%s', received_at) AS REAL) as received_at_unix, power_watts
            FROM power_readings
            WHERE source_device_id = ?
              AND strftime('%s', received_at) BETWEEN ? AND ?
              AND received_at IS NOT NULL
              AND power_watts IS NOT NULL
            ORDER BY received_at ASC
        ''', (device_id, start_ts, end_ts))

        for row in cursor.fetchall():
            # Ensure timestamp is not None before adding
            if row['received_at_unix'] is not None:
                try:
                    timestamp_float = float(row['received_at_unix'])
                    power_float = float(row['power_watts'])
                    data.append({
                        # Rename key for clarity in API response
                        'timestamp': timestamp_float,
                        'power': round(power_float, 2)
                    })
                except (TypeError, ValueError):
                     current_app.logger.warning(f"Skipping historical data point due to invalid data: {row}")
                     continue # Skip if conversion fails

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error in get_historical_data for device {device_id}: {e}")
        data = [] # Return empty list on DB error
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_historical_data for device {device_id}: {e}", exc_info=True)
        data = [] # Return empty list on other errors

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
        current_app.logger.error(f"Unexpected error in get_distinct_devices: {e}", exc_info=True)
        devices = []

    return devices
