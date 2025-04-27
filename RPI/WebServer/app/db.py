# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/db.py
import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
import os

def get_db() -> sqlite3.Connection:
    """
    Connects to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        try:
            g.db = sqlite3.connect(
                db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable Write-Ahead Logging for better concurrency
            g.db.execute("PRAGMA journal_mode=WAL;")
            # Return rows as dictionary-like objects
            g.db.row_factory = sqlite3.Row
            current_app.logger.debug(f"Database connection opened: {db_path}")
        except sqlite3.Error as e:
            current_app.logger.error(f"Error connecting to database at {db_path}: {e}")
            # Propagate the error or handle it as needed
            raise  # Re-raise the exception to signal failure
    return g.db

def close_db(e=None):
    """
    Closes the database connection if it was opened. This function is
    automatically called by Flask after the request is handled.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
        current_app.logger.debug("Database connection closed.")

def init_db():
    """Clear existing data and create new tables (if needed)."""
    # This function might be more relevant if you manage schema creation here.
    # For now, we assume the MQTT script or populate_db handles table creation.
    db_path = current_app.config['DATABASE']
    if not os.path.exists(db_path):
         current_app.logger.warning(f"Database file not found at {db_path}. Ensure it's created by the MQTT script or populate_db.")
         # Optionally, you could create the DB and table here if desired.
         # conn = sqlite3.connect(db_path)
         # # ... create table logic ...
         # conn.close()
    else:
        current_app.logger.info(f"Database found at {db_path}.")
    # You could add schema validation here if needed

@click.command('init-db')
@with_appcontext
def init_db_command():
    """CLI command to initialize the database."""
    init_db()
    click.echo('Initialized the database (checked existence).')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db) # Call close_db when app context tears down
    app.cli.add_command(init_db_command) # Add the 'flask init-db' command
    # Add basic logging configuration
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        # Example: Log to a file in production
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/webserver.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('WebServer startup')
