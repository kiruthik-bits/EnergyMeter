# Energy Monitoring Web Server

This repository contains a Flask web application designed to display energy consumption data stored in an SQLite database. It provides a web interface showing:

1.  A **Dashboard** with the latest power reading for each monitored device and the total current power consumption across all devices.
2.  A **History** page displaying historical power consumption data for selected devices over chosen time ranges using interactive charts.

The application uses a modular structure with Flask Blueprints, an application factory pattern, and dynamically updates data using JavaScript and API endpoints.

---

## Table of Contents

- [Application Structure](#application-structure)
- [Core Components](#core-components)
  - [Backend (Flask Application)](#backend-flask-application)
  - [Frontend (Templates & Static Files)](#frontend-templates--static-files)
  - [Database](#database)
  - [Test Scripts](#test-scripts)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [How to Run](#how-to-run)
- [API Endpoints](#api-endpoints)

---

## Application Structure

The `WebServer` directory is organized using a standard Flask application factory pattern:

```
WebServer/
├── app/                  # Main application package
│   ├── __init__.py       # App factory, blueprint registration
│   ├── config.py         # Configuration settings
│   ├── db.py             # Database connection setup & teardown
│   ├── main/             # Blueprint for core UI routes
│   │   ├── __init__.py
│   │   └── routes.py     # Routes for '/', '/history'
│   ├── api/              # Blueprint for API routes
│   │   ├── __init__.py
│   │   └── routes.py     # Routes for '/api/...'
│   └── models.py         # Data fetching logic (database queries)
├── static/
│   ├── css/
│   │   └── style.css     # Custom styles (can supplement Bootstrap)
│   └── js/
│       ├── dashboard.js  # JS for index.html
│       └── history.js    # JS for history.html
├── templates/
│   ├── base.html         # Base HTML template
│   ├── index.html        # Dashboard page template
│   └── history.html      # History page template
├── run.py                # Script to run the Flask development server
└── Test/                 # (Keep test scripts, update paths if needed)
    ├── populate_db.py
    └── data_feeder.py

```


---

## Core Components

### Backend (Flask Application)

-   **`run.py`**: The entry point script used to start the Flask development server. It imports the application factory.
-   **`app/__init__.py`**: Contains the `create_app` application factory. It initializes the Flask app, loads configuration, initializes extensions (like database handling), and registers blueprints.
-   **`app/config.py`**: Defines configuration classes (e.g., `DevelopmentConfig`, `ProductionConfig`) and loads settings from environment variables or defaults. Manages the database path and secret key.
-   **`app/db.py`**: Manages the SQLite database connection using Flask's application context (`g`). Provides `get_db` to access the connection and `close_db` for cleanup. Includes a `flask init-db` command.
-   **`app/models.py`**: Contains functions (`get_latest_stats`, `get_historical_data`, `get_distinct_devices`) that encapsulate the SQL queries needed to fetch data from the database.
-   **`app/main/` (Blueprint)**: Handles routes for serving the main user interface pages (`/` for the dashboard and `/history` for the historical data page). Uses `render_template` to serve HTML.
-   **`app/api/` (Blueprint)**: Handles routes prefixed with `/api`. These routes return data in JSON format, used by the frontend JavaScript to update pages dynamically. Includes endpoints for latest data, device lists, and historical data.

### Frontend (Templates & Static Files)

-   **`templates/base.html`**: The main Jinja2 template that provides the overall page structure, including the navigation bar (using Bootstrap), footer, and inclusion of CSS/JS files. Other templates extend this base.
-   **`templates/index.html`**: Template for the dashboard page. Displays the total power and placeholders for device cards. Extends `base.html`.
-   **`templates/history.html`**: Template for the historical data page. Includes dropdowns for device and time range selection, and a canvas element for the Chart.js graph. Extends `base.html`.
-   **`static/css/style.css`**: Contains minimal custom CSS rules. Most styling is handled by Bootstrap 5, included via CDN in `base.html`.
-   **`static/js/dashboard.js`**: JavaScript for the dashboard page (`index.html`). Fetches data from `/api/data` at regular intervals and updates the total power display and device cards.
-   **`static/js/history.js`**: JavaScript for the history page (`history.html`). Fetches the list of devices from `/api/devices` to populate the dropdown. Fetches historical data from `/api/historical_data` based on user selections and uses Chart.js (with Luxon adapter) to render the power consumption graph.

### Database

-   **`power_data.db`**: An SQLite database file located in the parent `RPI` directory. It is expected to contain the `power_readings` table. See Configuration for schema details.

### Test Scripts

-   **`Test/populate_db.py`**: A utility script to create the database table (if it doesn't exist) and populate it with sample historical data for testing.
-   **`Test/data_feeder.py`**: A utility script to simulate live data by inserting new random readings into the database at regular intervals.

---

## Prerequisites

1.  **Python 3:** Ensure Python 3 is installed. Check with `python3 --version`.
2.  **Flask:** Install Flask using pip:
    ```bash
    pip3 install Flask
    ```
    *(Other dependencies like `sqlite3`, `os`, `datetime`, `time` are typically included with Python.)*
3.  **Database:** The `power_data.db` file must exist in the `RPI/` directory and be accessible.

---

## Configuration

1.  **Database File (`power_data.db`):**
    -   The application expects the SQLite database file in the `RPI` directory (one level above `WebServer`).
    -   The database must contain a table named `power_readings` (schema defined in `Test/populate_db.py` and used by `app/models.py`). Key columns:
        -   `source_device_id` (TEXT)
        -   `power_watts` (REAL)
        -   `timestamp_unix` (REAL) - Unix epoch time (seconds).
        -   `received_at` (TIMESTAMP) - Fallback for sorting.
    -   The database is typically created/populated by the MQTT logger script or the test scripts (`populate_db.py`, `data_feeder.py`).

2.  **Environment Variables (Optional):**
    -   `FLASK_CONFIG`: Set to `development` (default) or `production` to select the configuration from `app/config.py`.
    -   `SECRET_KEY`: Set a strong secret key, especially for production environments. A default is provided in `app/config.py` for development.
    -   `FLASK_RUN_HOST`, `FLASK_RUN_PORT`: Can be used to configure the host and port when using `flask run`.

---

## How to Run

1.  **Ensure Prerequisites and Configuration:**
    -   Verify Python 3 and Flask are installed.
    -   Ensure `power_data.db` exists in the `RPI/` directory with the correct table structure. You can run `python3 Test/populate_db.py` once to ensure this.

2.  **Open a Terminal:**
    -   Access the command line on the machine where the code resides (e.g., your Raspberry Pi).

3.  **Navigate to the `WebServer` Directory:**
    ```bash
    cd /path/to/EnergyMeter/RPI/WebServer/
    ```
    *(Replace `/path/to/` with the actual path.)*

4.  **Set Flask Environment Variables:** (Required for Flask CLI)
    *   Linux/macOS:
        ```bash
        export FLASK_APP=run.py
        export FLASK_ENV=development # Optional: enables debug mode
        ```
    *   Windows CMD:
        ```bash
        set FLASK_APP=run.py
        set FLASK_ENV=development
        ```
    *   Windows PowerShell:
        ```powershell
        $env:FLASK_APP = "run.py"
        $env:FLASK_ENV = "development"
        ```

5.  **(Optional) Initialize Database (Checks Existence):**
    ```bash
    flask init-db
    ```

6.  **Run the Flask Application:**
    *   **Method 1: Using Flask CLI (Recommended)**
        ```bash
        flask run --host=0.0.0.0 --port=5000
        ```
        *(Listens on all network interfaces on port 5000)*
    *   **Method 2: Using Python directly**
        ```bash
        python3 run.py
        ```
        *(Reads host/port from environment or defaults to 0.0.0.0:5000)*

7.  **Observe Output:**
    -   The terminal will display output indicating the server is running, similar to:
        ```
         * Environment: development
         * Debug mode: on
         * Running on all addresses (0.0.0.0)
         * Running on http://127.0.0.1:5000
         * Running on http://<your_rpi_ip_address>:5000
        Press CTRL+C to quit
        ```

8.  **Access the Application:**
    -   Open a web browser on any device on the same network.
    -   Navigate to `http://<your_rpi_ip_address>:5000/` for the Dashboard.
    -   Navigate to `http://<your_rpi_ip_address>:5000/history` for the History page.
    *(Replace `<your_rpi_ip_address>` with the actual IP address of your Raspberry Pi).*

9.  **Stop the Server:**
    -   Press `Ctrl+C` in the terminal where the server is running.

---

## API Endpoints

The application provides the following API endpoints under the `/api` prefix:

-   **`GET /api/data`**: Returns the latest power reading for each device and the total power as a JSON object. Used by the dashboard.
-   **`GET /api/devices`**: Returns a JSON list of distinct `source_device_id` strings found in the database. Used by the history page dropdown.
-   **`GET /api/historical_data`**: Returns historical power readings for a specific device over a given time range.
    -   **Query Parameters:**
        -   `device_id` (string, required): The ID of the device to fetch data for.
        -   `hours` (integer, required): The number of past hours to retrieve data for (e.g., `1`, `24`, `168`).
    -   **Returns:** A JSON array of objects, each containing `timestamp` (ISO 8601 string) and `power` (float). Used by the history page chart.

---


