# Energy Meter - MQTT Data Logging and Web Monitoring System

A system for reading energy meter data (or simulating it), sending it via MQTT, storing it in an SQLite database on a Raspberry Pi, and providing a web interface for monitoring and visualization.

---

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Components Description](#components-description)
   - [ESP8266 Firmware](#esp8266-firmware)
   - [Raspberry Pi MQTT Scripts](#raspberry-pi-mqtt-scripts)
   - [Raspberry Pi Web Server](#raspberry-pi-web-server)
4. [System Workflow](#system-workflow)
5. [Setup and Installation](#setup-and-installation)
   - [Prerequisites](#prerequisites)
   - [ESP8266 Setup](#esp8266-setup)
   - [Raspberry Pi Setup](#raspberry-pi-setup)
6. [Running the System](#running-the-system)
7. [Checking the Data](#checking-the-data)
8. [Error Handling Notes](#error-handling-notes)
9. [Contributing](#contributing)
10. [Acknowledgments](#acknowledgments)

---

## Overview

The system consists of three main components:

1. **ESP8266 Microcontroller**: Publishes energy data to an MQTT broker.
2. **Raspberry Pi MQTT Logger**: Subscribes to MQTT topics and stores data in an SQLite database.
3. **Raspberry Pi Web Server**: Provides a web interface for monitoring device status and visualizing historical data.

---

## File Structure

```
EnergyMeter/
├── ESP8266/
│   ├── receive_data_send_mqtt.ino       # Reads serial data, sends to MQTT
│   ├── Test/
│   │   └── dummy_data_send_mqtt.ino     # Generates dummy data, sends to MQTT
│   └── README.md                        # ESP8266 component documentation
├── RPI/
│   ├── power_data.db                    # SQLite database
│   ├── MQTT/
│   │   ├── receive_mqtt_store_db.py     # Subscribes to MQTT, stores in DB
│   │   ├── Test/
│   │   │   ├── mqtt_data_to_db.py       # Subscribes to dummy MQTT topic
│   │   │   ├── print_power_db.py        # Prints database contents
│   │   │   └── README.md                # MQTT test scripts documentation
│   │   └── README.md                    # MQTT component documentation
│   └── WebServer/
│       ├── app/                         # Flask application package
│       │   ├── __init__.py              # Application factory
│       │   ├── config.py                # Configuration classes
│       │   ├── db.py                    # Database connection handling
│       │   ├── models.py                # Database query logic
│       │   ├── main/                    # Main UI routes (Blueprint)
│       │   └── api/                     # API routes (Blueprint)
│       ├── static/                      # Static assets (CSS, JS)
│       ├── templates/                   # Jinja2 HTML templates
│       ├── run.py                       # Entry point script
│       ├── Test/                        # Test scripts for WebServer
│       └── README.md                    # WebServer component documentation
└── README.md                            # Overall project documentation
```

---

## Components Description

### ESP8266 Firmware

- **`receive_data_send_mqtt.ino`**: Reads data from a serial device, parses it, and publishes it as JSON to an MQTT topic.
- **`dummy_data_send_mqtt.ino`**: Simulates power readings and publishes dummy data to a test MQTT topic.

### Raspberry Pi MQTT Scripts

- **`receive_mqtt_store_db.py`**: Subscribes to MQTT topics, parses incoming JSON messages, and stores data in an SQLite database.
- **Test Scripts**:
  - **`mqtt_data_to_db.py`**: Subscribes to a test MQTT topic and stores dummy data in the database.
  - **`print_power_db.py`**: Prints the contents of the database for verification.

### Raspberry Pi Web Server

- **Flask Application**:
  - **Dashboard (`/`)**: Displays active devices, latest readings, and device statuses.
  - **History (`/history`)**: Visualizes historical power consumption using Plotly.js.
  - **Statistics (`/statistics`)**: Calculates and displays metrics like average power and total energy consumption.
- **API Endpoints**: Provides RESTful APIs for fetching data used by the frontend.

---

## System Workflow

1. ESP8266 publishes energy data to an MQTT topic.
2. Raspberry Pi MQTT Logger subscribes to the topic and stores data in an SQLite database.
3. Raspberry Pi Web Server queries the database and serves data to the web interface.
4. Users access the web interface to monitor device status and visualize data.

---

## Setup and Installation

### Prerequisites

- **Hardware**:
  - ESP8266-based board (e.g., NodeMCU).
  - Raspberry Pi (Model 3B+ or newer).
- **Software**:
  - MQTT broker (e.g., Mosquitto).
  - Python 3 and pip.
  - Arduino IDE or PlatformIO for ESP8266 firmware.

### ESP8266 Setup

1.  **Install Arduino IDE/PlatformIO:** Set up your preferred development environment for the ESP8266.
2.  **Install Libraries:** Using the Library Manager in Arduino IDE (or `platformio.ini` for PlatformIO), install:
    *   `PubSubClient` (by Nick O'Leary)
    *   `ArduinoJson` (by Benoit Blanchon)
    *   `NTPClient` (by Fabrice Weinberg) - *If using NTP for timestamps in the firmware.*
    *   `ESP8266WiFi` (usually included with the ESP8266 board package)
3.  **Configure Sketch:**
    *   Open either `ESP8266/receive_data_send_mqtt.ino` (for real data) or `ESP8266/Test/dummy_data_send_mqtt.ino` (for testing).
    *   Modify the following constants near the top of the file:
        *   `WIFI_SSID`: Your WiFi network name.
        *   `WIFI_PASSWORD`: Your WiFi password.
        *   `MQTT_BROKER`: The IP address or hostname of your MQTT broker.
        *   `MQTT_PORT`: The port your MQTT broker is listening on (usually 1883).
        *   `MQTT_TOPIC`: Ensure this matches the topic the RPi logger script will subscribe to (e.g., `sensors/power/serial` or `sensors/power/dummy`).
        *   `DEVICE_ID`: A unique identifier for this specific ESP8266 device.
4.  **Upload Firmware:** Compile and upload the configured sketch to your ESP8266 board. Monitor the Serial Monitor for connection status and data publishing messages.

### Raspberry Pi Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url> # Replace with your repository URL
    cd EnergyMeter
    ```
2.  **Install MQTT Broker (Optional, if hosting locally):**
    ```bash
    sudo apt update
    sudo apt install mosquitto mosquitto-clients -y
    sudo systemctl enable mosquitto # Start on boot
    sudo systemctl start mosquitto
    ```
3.  **Set up MQTT Logger:**
    *   Navigate to the MQTT directory: `cd RPI/MQTT`
    *   Edit `receive_mqtt_store_db.py` (or `Test/mqtt_data_to_db.py` if testing) and configure:
        *   `MQTT_BROKER`: IP/hostname of your broker.
        *   `MQTT_PORT`: Broker port.
        *   `MQTT_TOPIC`: The topic the ESP8266 is publishing to (must match).
        *   `DATABASE_FILE`: Verify the path points correctly to `../power_data.db`.
    *   Install the required Python library:
        ```bash
        pip3 install paho-mqtt
        ```
4.  **Set up Web Server:**
    *   Navigate to the WebServer directory: `cd ../WebServer` (if you were in `RPI/MQTT`) or `cd RPI/WebServer` (if you were in `EnergyMeter`).
    *   **Create and activate a Python virtual environment (Recommended):**
        ```bash
        python3 -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   **Install required Python libraries:**
        ```bash
        pip install Flask
        # If a requirements.txt file is added later, use: pip install -r requirements.txt
        ```
    *   **Prepare the Database:** Ensure the `power_data.db` file exists in the `RPI/` directory (one level above `WebServer`). If not, you can:
        *   Run the MQTT logger script (`RPI/MQTT/receive_mqtt_store_db.py`) and wait for the ESP8266 to send data.
        *   *OR* Use a test population script:
            ```bash
            cd Test/
            python3 populate_db.py # For a small amount of historical data
            # OR
            # python3 populate_week.py # For more extensive historical data
            cd .. # Go back to WebServer directory
            ```

---

## Running the System

1.  **Start the MQTT Broker:** Ensure your MQTT broker is running.
2.  **Power on the ESP8266:** It should connect to WiFi and start publishing data.
3.  **Start the MQTT Logger Script:**
    *   Open a terminal on the Raspberry Pi.
    *   Navigate to the MQTT logger directory: `cd /path/to/EnergyMeter/RPI/MQTT`
    *   Run the appropriate script (use `nohup` or a terminal multiplexer like `screen` or `tmux` for continuous background operation):
        ```bash
        # For real data
        nohup python3 receive_mqtt_store_db.py > mqtt_logger.log 2>&1 &

        # OR for dummy data
        # nohup python3 Test/mqtt_data_to_db.py > mqtt_test_logger.log 2>&1 &
        ```
    *   You can check the log file (`mqtt_logger.log` or `mqtt_test_logger.log`) for messages.
4.  **Start the Flask Web Server:**
    *   Open another terminal on the Raspberry Pi.
    *   Navigate to the WebServer directory: `cd /path/to/EnergyMeter/RPI/WebServer`
    *   Activate the virtual environment (if used): `source venv/bin/activate`
    *   Set required environment variables for Flask:
        ```bash
        export FLASK_APP=run.py
        export FLASK_ENV=development # Use 'production' for deployment (disables debug mode)
        # Optional: Make accessible on your network (replace 0.0.0.0 with RPi IP if needed)
        export FLASK_RUN_HOST=0.0.0.0
        # Optional: Change port if 5000 is in use
        # export FLASK_RUN_PORT=5001
        ```
    *   Run the Flask development server:
        ```bash
        flask run
        ```
    *   The output will show the address the server is running on (e.g., `http://0.0.0.0:5000/`).
5.  **Access the Web Application:**
    *   Open a web browser on a device connected to the same network as the Raspberry Pi.
    *   Navigate to `http://<your_raspberry_pi_ip_address>:5000` (replace `<your_raspberry_pi_ip_address>` with the actual IP of your RPi and use the correct port if you changed it).

---

## Checking the Data

1.  **Database Content:** Use the `print_power_db.py` script to view the raw database contents directly in the terminal:
    ```bash
    # Navigate to RPI/MQTT/Test first
    python3 /path/to/EnergyMeter/RPI/MQTT/Test/print_power_db.py
    ```
2.  **Web Application:** Access the different pages via your browser:
    *   **Dashboard (`/`)**: View the current status (Active/Inactive), latest power reading, and last update time for all devices. Check the "Devices Online" count.
    *   **History (`/history`)**: Select a device and a time range (e.g., Last Hour, Last 24 Hours) to see its power consumption graph rendered by Plotly.js.
    *   **Statistics (`/statistics`)**: Select a device and time range to view calculated metrics like Average Power, Peak Usage, and Total Energy Consumption (kWh).

---

## Error Handling Notes

-   **ESP8266:**
    *   Includes retry logic for MQTT publishing failures with delays.
    *   Attempts to reconnect to WiFi and MQTT if the connection is lost.
    *   Uses Serial prints for debugging connection and publishing status.
-   **Raspberry Pi (MQTT Logger):**
    *   Uses SQLite transactions (`conn.commit()`, `conn.rollback()`) for atomic database writes, reducing the risk of partial data insertion on error.
    *   Handles potential JSON parsing errors and logs issues.
    *   The `paho-mqtt` library handles MQTT reconnections automatically after network interruptions.
    *   Logs connection status, received messages, and database errors to the console (or log file if using `nohup`).
-   **Raspberry Pi (Web Server):**
    *   Uses `try...except` blocks in API routes and database model functions (`app/models.py`) to catch potential `sqlite3.Error` or other exceptions during database operations.
    *   Returns appropriate JSON error responses with HTTP status codes (e.g., 400 for bad requests, 500 for server errors) from the API.
    *   Frontend JavaScript includes error handling for `fetch` requests and displays user-friendly error messages on the web pages if data cannot be loaded or processed.
    *   Checks for database file existence before rendering pages and shows an error if it's missing.
    *   Uses Flask's built-in logging to record application events and errors (configured in `app/db.py` for production).

---

## Acknowledgments

*   Libraries used: PubSubClient, ArduinoJson, NTPClient, paho-mqtt, Flask, Plotly.js, Bootstrap.
*   Inspired by various IoT energy monitoring projects.

---
