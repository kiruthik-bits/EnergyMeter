# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/main/__init__.py
from flask import Blueprint

# Create a Blueprint instance for main routes
main_bp = Blueprint('main', __name__, template_folder='../../templates', static_folder='../../static')

# Import routes after creating the blueprint to avoid circular imports
from . import routes
