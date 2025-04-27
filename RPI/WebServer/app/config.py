# /home/kiruthik/Documents/Mtech/SEM1/SES/Assignment1/EnergyMeter/RPI/WebServer/app/config.py
import os

# Determine the absolute path to the RPI directory
# __file__ is .../WebServer/app/config.py
# os.path.dirname(__file__) is .../WebServer/app
# os.path.join(..., '..') is .../WebServer
# os.path.join(..., '..') is .../RPI
RPI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Construct the absolute path to the database file within the RPI directory
DATABASE_PATH = os.path.join(RPI_DIR, 'power_data.db')

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key' # Important for sessions, flash messages etc.
    # Use the correctly calculated absolute path
    DATABASE = DATABASE_PATH
    DEBUG = False
    TESTING = False
    # Add other default settings here

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    # Override settings for production (e.g., DEBUG=False)
    # You might fetch SECRET_KEY strictly from environment variables here
    pass

# Dictionary to access configurations by name
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Function to get the database path easily (optional, but good practice)
def get_database_path():
    """Returns the configured absolute path to the database."""
    return DATABASE_PATH

