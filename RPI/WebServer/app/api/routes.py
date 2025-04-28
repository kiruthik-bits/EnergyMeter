# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/api/routes.py
from flask import jsonify, request, current_app, abort
from . import api_bp

from ..models import (
    get_latest_stats,
    get_historical_data,
    get_distinct_devices,
    calculate_average_power,
    find_peak_usage,
    calculate_total_energy_kwh
)

def error_response(status_code: int, message: str = None):
    payload = {'error': message or 'An error occurred'}
    response = jsonify(payload)
    response.status_code = status_code
    return response

@api_bp.route('/data')
def latest_data():
    """Provides the latest power data and received_at timestamp (Unix epoch)."""
    try:
        stats = get_latest_stats()
        if 'error' in stats:
            return error_response(500, stats['error'])
        # The keys returned by get_latest_stats are now 'latest' and 'latest_timestamp_unix'
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Unhandled exception in /api/data: {e}", exc_info=True)
        return error_response(500, "An internal server error occurred while fetching latest data.")


@api_bp.route('/devices')
def devices_list():
    """Provides a list of distinct device IDs."""
    # No changes needed here
    try:
        devices = get_distinct_devices()
        return jsonify(devices)
    except Exception as e:
        current_app.logger.error(f"Unhandled exception in /api/devices: {e}", exc_info=True)
        return error_response(500, "An internal server error occurred while fetching device list.")


@api_bp.route('/historical_data')
def historical_data():
    """Provides historical power data with received_at timestamps (Unix epoch)."""
    device_id = request.args.get('device_id')
    hours_str = request.args.get('hours', '1')

    if not device_id:
        return error_response(400, "Missing 'device_id' query parameter.")

    try:
        time_range_hours = int(hours_str)
        if time_range_hours <= 0:
            raise ValueError("Hours must be positive.")
    except (ValueError, TypeError):
        return error_response(400, f"Invalid 'hours' parameter: '{hours_str}'. Must be a positive integer.")

    try:
        data = get_historical_data(device_id, time_range_hours)
        # get_historical_data now returns 'timestamp' as Unix epoch float
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Unhandled exception in /api/historical_data for device {device_id}: {e}", exc_info=True)
        return error_response(500, f"An internal server error occurred while fetching historical data for {device_id}.")

@api_bp.route('/statistics')
def statistics_data():
    """Provides calculated statistics using received_at timestamps."""
    device_id = request.args.get('device_id')
    hours_str = request.args.get('hours', '24')

    if not device_id:
        return error_response(400, "Missing 'device_id' query parameter.")

    try:
        time_range_hours = int(hours_str)
        if time_range_hours <= 0:
            raise ValueError("Hours must be positive.")
    except (ValueError, TypeError):
        return error_response(400, f"Invalid 'hours' parameter: '{hours_str}'. Must be a positive integer.")

    try:
        avg_power = calculate_average_power(device_id, time_range_hours)
        peak_usage = find_peak_usage(device_id, time_range_hours) # Now returns {'timestamp_unix': ..., 'power': ...}
        total_energy = calculate_total_energy_kwh(device_id, time_range_hours)

        stats = {
            'device_id': device_id,
            'time_range_hours': time_range_hours,
            'average_power_watts': avg_power,
            'peak_usage': peak_usage, # Contains 'timestamp_unix' (Unix epoch float)
            'total_energy_kwh': total_energy
        }
        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Unhandled exception in /api/statistics for device {device_id}: {e}", exc_info=True)
        return error_response(500, f"An internal server error occurred while calculating statistics for {device_id}.")

