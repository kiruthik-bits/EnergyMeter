# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/main/routes.py
from flask import render_template, current_app, abort
import os
from . import main_bp # Import the blueprint instance

from ..db import get_db # To check DB existence

@main_bp.route('/')
def index():
    """Serves the main dashboard page."""
    # Check if the database file exists before rendering
    db_path = current_app.config['DATABASE']
    if not os.path.exists(db_path):
         current_app.logger.error(f"Database file not found at {db_path} for index route.")
         # Use abort to return a standard HTTP error page
         abort(500, description=f"Database file not found at {db_path}. Please ensure the MQTT script or populate script has run.")
    return render_template('index.html', title="Dashboard")

@main_bp.route('/history')
def history():
    """Serves the historical data page."""
    db_path = current_app.config['DATABASE']
    if not os.path.exists(db_path):
         current_app.logger.error(f"Database file not found at {db_path} for history route.")
         abort(500, description=f"Database file not found at {db_path}. Please ensure the MQTT script or populate script has run.")
    return render_template('history.html', title="History")

@main_bp.route('/statistics')
def statistics():
    """Serves the statistics page."""
    db_path = current_app.config['DATABASE']
    if not os.path.exists(db_path):
         current_app.logger.error(f"Database file not found at {db_path} for statistics route.")
         abort(500, description=f"Database file not found at {db_path}. Please ensure the MQTT script or populate script has run.")
    # Pass title to the template
    return render_template('statistics.html', title="Statistics")

