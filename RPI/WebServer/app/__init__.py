# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/__init__.py
from flask import Flask
import os
# Import timezone along with datetime
from datetime import datetime, timezone

from .config import config_by_name, get_database_path
from . import db # Import the db module

def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    # --- Explicitly define static folder and URL path here ---
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder='../static',  # Path relative to this file (__init__.py)
        static_url_path='/static'   # The URL path to serve static files from
    )
    # --- End modification ---

    # Load configuration
    app.config.from_object(config_by_name[config_name])
    # Load instance config if it exists (e.g., instance/config.py)
    # app.config.from_pyfile('config.py', silent=True)

    # Ensure the instance folder exists if you use it
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions/modules
    db.init_app(app) # Initialize database handling

    # Register Blueprints
    from .main import main_bp
    app.register_blueprint(main_bp)

    from .api import api_bp
    app.register_blueprint(api_bp)

    # --- Add Context Processor ---
    @app.context_processor
    def inject_now():
        """Injects the current UTC datetime into the template context."""
        # Use the recommended timezone-aware method
        return {'now': datetime.now(timezone.utc)}
    # --- End Context Processor ---


    # Check database existence on startup (optional, but helpful)
    with app.app_context():
        db_path = get_database_path()
        if not os.path.exists(db_path):
             app.logger.warning(f"DATABASE NOT FOUND at {db_path}. Ensure it is created before accessing pages.")
        else:
             app.logger.info(f"Database found at {db_path}")


    # Add a simple health check endpoint (optional)
    @app.route('/health')
    def health_check():
        # You could add a quick DB check here too if desired
        return "OK", 200

    app.logger.info(f"Flask app created with '{config_name}' configuration.")
    return app
