# Energy Meter - MQTT Data Logging and Web Monitoring System

This project implements a system for reading energy meter data (or simulating it), sending it via MQTT, storing it persistently in a database on a Raspberry Pi, and displaying the latest readings via a web interface.

---

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Components Description](#components-description)
  - [ESP8266 Firmware](#esp8266-firmware)
  - [Raspberry Pi MQTT Scripts](#raspberry-pi-mqtt-scripts)
  - [Raspberry Pi Web Server](#raspberry-pi-web-server)
- [System Workflow](#system-workflow)
- [Setup and Installation](#setup-and-installation)
  - [Prerequisites](#prerequisites)
  - [ESP8266 Setup](#esp8266-setup)
  - [Raspberry Pi Setup](#raspberry-pi-setup)
- [Running the System](#running-the-system)
- [Checking the Data](#checking-the-data)
- [Error Handling Notes](#error-handling-notes)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

The system consists of three main parts:

1. **ESP8266 Microcontroller:** Responsible for gathering power data and publishing it to an MQTT broker. Two versions are provided:
   - One reads data from an external device via a serial connection.
   - One generates dummy data internally for testing purposes.
2. **Raspberry Pi (RPI) - MQTT Logger:** Runs Python scripts that subscribe to MQTT topics, receive the data published by the ESP8266, and store it in an SQLite database (`power_data.db`).
3. **Raspberry Pi (RPI) - Web Server:** Runs a Flask web application that reads the latest data from the SQLite database and presents it on a simple dashboard webpage, which updates automatically.

Communication between the ESP8266 and the RPI logger happens via an MQTT broker. The web server directly accesses the database populated by the logger.

---

## File Structure

```
EnergyMeter/
├── ESP8266/
│   ├── receive_data_send_mqtt.ino       # Reads serial data, sends to MQTT (sensors/power/serial)
│   ├── README.md                        # README for receive_data_send_mqtt.ino
│   └── Test/
│       ├── dummy_data_send_mqtt.ino     # Generates dummy data, sends to MQTT (sensors/power/dummy)
│       └── README.md                    # README for dummy_data_send_mqtt.ino
├── RPI/
│   ├── power_data.db                    # SQLite database file (created by logger/test scripts)
│   ├── MQTT/
│   │   ├── receive_mqtt_store_db.py     # Subscribes to real data topic, stores in DB
│   │   ├── README.md                    # README for receive_mqtt_store_db.py
│   │   └── Test/
│   │       ├── mqtt_data_to_db.py       # Subscribes to dummy data topic, stores in DB
│   │       ├── print_power_db.py        # Utility to print DB contents
│   │       └── README.md                # README for MQTT/Test scripts
│   └── WebServer/
│       ├── app.py                       # Flask web application backend
│       ├── static/
│       │   └── style.css                # CSS for the web interface
│       ├── templates/
│       │   └── index.html               # HTML template for the dashboard
│       ├── README.md                    # README for the WebServer component
│       └── Test/
│           ├── populate_db.py           # Script to add initial bulk data to DB
│           ├── data_feeder.py           # Script to continuously add test data to DB
│           └── README.md                # README for WebServer/Test scripts
└── README.md                            # This file (Overall Project README)
```

---

## Components Description

### ESP8266 Firmware

- **`ESP8266/receive_data_send_mqtt.ino`:**
  - Connects to WiFi and an MQTT broker.
  - Reads data from a serial device, parses it, and publishes it as JSON to an MQTT topic.
  - Includes retry logic for MQTT publishing failures.

- **`ESP8266/Test/dummy_data_send_mqtt.ino`:**
  - Simulates power readings for testing purposes.
  - Publishes dummy data to a test MQTT topic.

### Raspberry Pi MQTT Scripts

- **`RPI/MQTT/receive_mqtt_store_db.py`:**
  - Subscribes to a real data MQTT topic.
  - Parses and validates incoming JSON messages.
  - Stores the data in an SQLite database (`power_data.db`).

- **`RPI/MQTT/Test/mqtt_data_to_db.py`:**
  - Similar to `receive_mqtt_store_db.py` but subscribes to a test MQTT topic.
  - Used for testing the database logging functionality.

- **`RPI/MQTT/Test/print_power_db.py`:**
  - Prints the contents of the `power_data.db` database to the console.

### Raspberry Pi Web Server

- **`RPI/WebServer/app.py`:**
  - A Flask web application that serves a dashboard displaying the latest power readings.
  - Provides an API endpoint (`/data`) for fetching data from the database.

- **`RPI/WebServer/templates/index.html`:**
  - The HTML structure for the web dashboard.
  - Includes JavaScript for dynamically updating the dashboard with data from the `/data` endpoint.

- **`RPI/WebServer/static/style.css`:**
  - Styles the web dashboard.

---

## System Workflow

1. **ESP8266:** Reads or generates power data and publishes it to an MQTT topic.
2. **MQTT Broker:** Forwards the data to subscribed clients.
3. **Raspberry Pi (MQTT Logger):** Subscribes to the MQTT topic, processes the data, and stores it in an SQLite database.
4. **Raspberry Pi (Web Server):** Reads the data from the database and displays it on a web dashboard.

---

## Setup and Installation

### Prerequisites

1. **MQTT Broker:** Install and configure an MQTT broker (e.g., Mosquitto).
2. **Arduino IDE or PlatformIO:** For compiling and uploading firmware to the ESP8266.
3. **Python 3:** Ensure Python 3 is installed on the Raspberry Pi.
4. **Required Python Libraries:** Install `paho-mqtt` and `Flask`:
   ```bash
   pip3 install paho-mqtt Flask
   ```

### ESP8266 Setup

1. Install the required libraries (`PubSubClient`, `ArduinoJson`, `NTPClient`) in the Arduino IDE.
2. Configure the sketch with your WiFi and MQTT broker details.
3. Upload the sketch to the ESP8266.

### Raspberry Pi Setup

1. Clone the repository to your Raspberry Pi.
2. Configure the MQTT logger scripts with your MQTT broker details.
3. Ensure the `power_data.db` database is created and accessible.

---

## Running the System

1. Start the MQTT logger script:
   ```bash
   python3 /path/to/EnergyMeter/RPI/MQTT/receive_mqtt_store_db.py
   ```
2. Start the Flask web server:
   ```bash
   python3 /path/to/EnergyMeter/RPI/WebServer/app.py
   ```
3. Access the web dashboard at `http://<your_rpi_ip_address>:5000`.

---

## Checking the Data

1. Use the `print_power_db.py` script to view the database contents:
   ```bash
   python3 /path/to/EnergyMeter/RPI/MQTT/Test/print_power_db.py
   ```
2. Access the web dashboard to view the latest readings.

---

## Error Handling Notes

- **ESP8266:**
  - Includes retry logic for MQTT publishing failures.
  - Restarts on WiFi connection failure.
- **Raspberry Pi (MQTT Logger):**
  - Uses SQLite transactions for atomic writes.
  - Handles MQTT reconnections automatically.
- **Raspberry Pi (Web Server):**
  - Handles database errors gracefully.
  - Returns default data or error messages if the database is unavailable.

---