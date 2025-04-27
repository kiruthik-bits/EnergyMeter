# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/run.py
import os
from app import create_app # Import the factory function

# Determine the configuration profile (e.g., 'development', 'production')
# Use environment variable or default to 'development'
config_name = os.getenv('FLASK_CONFIG', 'development')

app = create_app(config_name)

if __name__ == '__main__':
    # Get host and port from environment variables or use defaults
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('FLASK_RUN_PORT', '5000'))
    except ValueError:
        port = 5000

    # Use debug=True only in development
    use_debugger = app.config.get('DEBUG', False)

    print(f" * Starting Flask app with '{config_name}' config...")
    print(f" * Running on http://{host}:{port}")
    print(f" * Debug mode: {'on' if use_debugger else 'off'}")

    # app.run() handles host, port, and debug based on Flask's standard mechanisms
    # when run via `flask run` command.
    # For direct `python run.py`, we pass them explicitly:
    app.run(host=host, port=port, debug=use_debugger)

