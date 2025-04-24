# Energy Monitoring Web Server

This repository contains a simple Flask web application designed to display energy consumption data stored in an SQLite database. It provides a web interface showing the latest power reading for each monitored device and the total current power consumption across all devices. The data on the webpage updates automatically without requiring a full page reload.

---

## Table of Contents

- [Application Structure](#application-structure)
- [Core Components](#core-components)
  - [1. `app.py` (Flask Backend)](#1-app.py-flask-backend)
  - [2. `templates/index.html` (Frontend HTML)](#2-templatesindex.html-frontend-html)
  - [3. `static/style.css` (Frontend CSS)](#3-staticstyle.css-frontend-css)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [How to Run](#how-to-run)


---

## Application Structure

```
EnergyMeter/
└── RPI/
    ├── power_data.db  <-- Database file HERE
    ├── MQTT/
    │   ├── receive_mqtt_store_db.py
    │   └── ...
    └── WebServer/
        ├── app.py         <-- Flask app HERE
        ├── static/
        │   └── style.css
        ├── templates/
        │   └── index.html
        └── Test/
            ├── populate_db.py
            └── data_feeder.py
```

---

## Core Components

### 1. `app.py` (Flask Backend)

This script is the heart of the web application. It sets up a web server that interacts with the database and serves web pages/data to clients (browsers).

#### Key Functionalities:

- **Imports:** Necessary libraries like `Flask`, `render_template`, `jsonify`, `sqlite3`, and `os`.
- **Flask App Initialization:** Creates an instance of the Flask application: `app = Flask(__name__)`.
- **Database Connection (`get_db` function):**
  - Connects to the SQLite database (`power_data.db`) located one level above the `WebServer` directory.
  - Sets `conn.row_factory = sqlite3.Row` to allow accessing database columns by name.
- **Data Fetching Logic (`get_latest_stats` function):**
  - Queries the database to fetch the latest power readings for each device.
  - Calculates the total current power consumption.
  - Returns the data as a dictionary.
- **API Endpoint (`/data` route):**
  - Returns the latest power data as a JSON response.
  - Used by the frontend to dynamically update the dashboard.
- **Main Page Endpoint (`/` route):**
  - Serves the main dashboard page (`index.html`).
  - Checks if the database file exists before rendering the page.
- **Development Server Execution:**
  - Runs the Flask app on `0.0.0.0:5000` for network-wide access during development.

---

### 2. `templates/index.html` (Frontend HTML)

- Provides the basic structure for the dashboard page.
- Includes placeholders (`div` elements) for dynamic data injection.
- Contains embedded JavaScript to fetch data from the `/data` endpoint and update the dashboard every 5 seconds.

---

### 3. `static/style.css` (Frontend CSS)

- Defines the visual appearance of the dashboard, including layout, colors, and fonts.
- Styles the total power display and individual device cards.
- Includes responsive design for smaller screens.

---

## Prerequisites

1. **Python 3:** Ensure Python 3 is installed on your system. Check with:
   ```bash
   python3 --version
   ```
2. **Flask:** Install Flask using pip:
   ```bash
   pip3 install Flask
   ```

---

## Configuration

1. **Database File (`power_data.db`):**
   - The application expects a SQLite database file named `power_data.db` in the `RPI` directory.
   - The database must contain a table named `power_readings` with the following columns:
     - `source_device_id` (TEXT)
     - `power_watts` (REAL or NUMERIC)
     - `timestamp_unix` (REAL or NUMERIC) - Stores Unix epoch time.
     - `received_at` (TIMESTAMP or DATETIME) - Fallback for sorting.
   - The database is typically created and populated by the MQTT logger scripts (`receive_mqtt_store_db.py` or `mqtt_data_to_db.py`) or test scripts (`populate_db.py`, `data_feeder.py`).

---

## How to Run

1. **Ensure Prerequisites and Configuration:**
   - Verify that Python 3 and Flask are installed.
   - Ensure the `power_data.db` file exists in the correct location with the necessary table and columns.

2. **Open a Terminal:**
   - Access the command line on the machine where the code resides (e.g., your Raspberry Pi).

3. **Navigate to the `WebServer` Directory:**
   ```bash
   cd /path/to/EnergyMeter/RPI/WebServer/
   ```
   *(Replace `/path/to/` with the actual path to your project.)*

4. **Run the Flask Application:**
   ```bash
   python3 app.py
   ```

5. **Observe Output:**
   - The terminal will display output indicating the server is running:
     ```
     * Running on all addresses (0.0.0.0)
     * Running on http://127.0.0.1:5000
     * Running on http://<your_rpi_ip_address>:5000
     Press CTRL+C to quit
     ```

6. **Access the Dashboard:**
   - Open a web browser on any device connected to the same network as the server.
   - Navigate to `http://<your_rpi_ip_address>:5000/` (replace `<your_rpi_ip_address>` with the actual IP address of your Raspberry Pi).

7. **Stop the Server:**
   - Press `Ctrl+C` in the terminal to stop the Flask application.

---



