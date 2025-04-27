# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/api/__init__.py
from flask import Blueprint

# Create a Blueprint instance for API routes, prefixing all routes with /api
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes after creating the blueprint
from . import routes
