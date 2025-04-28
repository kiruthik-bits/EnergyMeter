# Energy Monitoring Web Server

A Flask-based web application for visualizing energy consumption data and monitoring device status from IoT devices stored in an SQLite database.

---

## Features

- **Dashboard**:
    - Displays the number of currently **active devices** (devices that sent data within the last minute).
    - Shows status cards for **all** registered devices.
    - Each device card indicates **Active/Inactive** status with visual cues (color, badge).
    - Displays the **latest power reading** and the **time since the last update** for each device.
    - Includes auto-refresh and manual refresh options.
    - Device cards are clickable, linking to the historical data page.
- **Historical Data Visualization**: Interactive charts (via Plotly.js) for power usage trends over various time ranges (1 hour to 30 days).
- **Device Statistics**: Key metrics like average power, peak usage, and total energy consumption (kWh) for selected devices over specified time ranges.
- **Modular Design**: Organized using Flask Blueprints and an application factory pattern.
- **Dynamic Updates**: Uses JavaScript (`fetch` API) and RESTful APIs for seamless updates without full page reloads.
- **Responsive UI**: Built with Bootstrap 5 for a clean and adaptive interface across different devices.

---

## Table of Contents

1. [Features](#features)
2. [Application Structure](#application-structure)
3. [Core Components](#core-components)
   - [Backend](#backend)
   - [Frontend](#frontend)
   - [Database](#database)
   - [Testing Utilities](#testing-utilities)
4. [Theory / Design Rationale](#theory--design-rationale)
   - [Framework Choice (Flask)](#framework-choice-flask)
   - [Application Structure (Factory Pattern & Blueprints)](#application-structure-factory-pattern--blueprints)
   - [Database Choice (SQLite)](#database-choice-sqlite)
   - [Frontend Technology (Bootstrap, Plotly.js, Vanilla JS)](#frontend-technology-bootstrap-plotlyjs-vanilla-js)
   - [API Design (RESTful)](#api-design-restful)
   - [Total Energy Calculation Method](#total-energy-calculation-method)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Configuration](#configuration)
8. [Running the Application](#running-the-application)
9. [Usage](#usage)
10. [API Endpoints](#api-endpoints)
11. [Testing Utilities](#testing-utilities)

---

## Application Structure

The `WebServer` directory follows a standard Flask structure:

```
EnergyMeter/
└── RPI/
    ├── power_data.db              # SQLite database
    ├── MQTT/                      # MQTT scripts
    └── WebServer/
        ├── app/                   # Core application package
        │   ├── __init__.py        # Application factory
        │   ├── config.py          # Configuration classes
        │   ├── db.py              # Database connection handling
        │   ├── models.py          # Database query logic
        │   ├── main/              # Main UI routes (Blueprint)
        │   └── api/               # API routes (Blueprint)
        ├── static/                # Static assets (CSS, JS)
        ├── templates/             # Jinja2 HTML templates
        ├── logs/                  # Log files
        ├── run.py                 # Entry point script
        └── Test/                  # Testing utilities
```


---

## Core Components

### Backend

- **`run.py`**: Entry point for running the Flask server.
- **`app/__init__.py`**: Application factory for initializing the app, extensions, and blueprints.
- **`app/config.py`**: Configuration classes for development and production.
- **`app/db.py`**: Manages SQLite connections and provides CLI commands (e.g., `flask init-db`).
- **`app/models.py`**: Encapsulates SQL queries for fetching and calculating data.
- **Blueprints**:
  - **`main/`**: Routes for UI pages (`/`, `/history`, `/statistics`).
  - **`api/`**: Routes for RESTful APIs (`/api/*`).

### Frontend

- **Templates**:
  - `base.html`: Base layout with Bootstrap and navigation.
  - `index.html`: Dashboard page displaying device status.
  - `history.html`: Historical data visualization page with Plotly charts.
  - `statistics.html`: Device statistics calculation and display page.
- **Static Files**:
  - `css/style.css`: Custom CSS styles.
  - `js/dashboard.js`: Logic for fetching data and updating the dashboard cards and active device count.
  - `js/history.js`: Logic for fetching device lists, historical data, and rendering Plotly charts.
  - `js/statistics.js`: Logic for fetching device lists, statistics data, and displaying results.

### Database

- **`power_data.db`**: SQLite database located in the parent `RPI` directory, containing the `power_readings` table.

### Testing Utilities

- **`Test/`**: Contains Python scripts (`populate_db.py`, `populate_week.py`, `data_feeder.py`) for initializing the database, adding historical sample data, and simulating live data feeds. See `Test/README.md` for details.

---

## Theory / Design Rationale

This section explains some of the key design choices made during the development of the `WebServer` application.

### Framework Choice (Flask)

*   **Flask** was chosen as the web framework primarily because it's a **microframework**. This means it provides the core essentials for web development (routing, request handling, templating) without imposing a rigid structure or including features that might not be needed (like an ORM or complex authentication systems out-of-the-box).
*   Its **simplicity** makes it relatively easy to get started with, especially for smaller projects or applications running on resource-constrained devices like a Raspberry Pi.
*   Flask's **flexibility** allows developers to choose and integrate the specific libraries and tools they need (e.g., choosing a specific charting library, database interaction method).

### Application Structure (Factory Pattern & Blueprints)

*   **Application Factory (`create_app` in `app/__init__.py`):** This pattern is used to create instances of the Flask application. It improves testability and allows for different configurations (e.g., development, production, testing) to be easily loaded. It avoids issues with global application objects.
*   **Blueprints (`app/main/` and `app/api/`):** Blueprints are used to organize the application into logical components.
    *   The `main` blueprint handles routes related to serving user-facing HTML pages.
    *   The `api` blueprint handles routes that serve data in JSON format, decoupling the backend data provision from the frontend presentation.
    *   This separation makes the codebase easier to navigate, maintain, and scale as new features are added.

### Database Choice (SQLite)

*   **SQLite** was selected for its **simplicity and ease of deployment**. As a file-based database, it doesn't require a separate database server process to be running, making it ideal for single-node applications or embedded systems like the Raspberry Pi.
*   For the scale of a typical home energy monitoring project, SQLite provides sufficient performance for querying historical data and statistics.
*   The database schema is kept straightforward, focusing on storing the core power readings efficiently. An index on the `timestamp_unix` column is used to speed up time-based queries.
*   **Write-Ahead Logging (WAL)** mode is enabled for database connections to improve concurrency by allowing readers to continue operating while data is being written.

### Frontend Technology (Bootstrap, Plotly.js, Vanilla JS)

*   **Bootstrap 5:** Used for the overall UI layout, styling, and responsiveness. It provides pre-built components (cards, navigation, grid system, spinners, alerts) that accelerate frontend development and ensure a consistent, modern look across different screen sizes.
*   **Plotly.js:** Chosen for rendering interactive charts on the history page. It offers good interactivity (zooming, panning, hover details) and handles date/time axes well, making it suitable for time-series data visualization.
*   **Vanilla JavaScript (with Fetch API):** Standard browser JavaScript is used for frontend logic. The `fetch` API is employed to make asynchronous requests to the backend API endpoints, allowing pages (like the dashboard, history, and statistics) to update dynamically or load data without requiring full page reloads. This provides a smoother user experience. Error handling and loading states are managed within the JavaScript.

### API Design (RESTful)

*   A separate API (using the `/api` blueprint) is implemented to provide data to the frontend JavaScript.
*   This follows RESTful principles, where specific endpoints are responsible for specific data resources (e.g., `/api/devices`, `/api/historical_data`, `/api/statistics`, `/api/data`).
*   This **decoupling** means the backend can be developed and tested independently of the frontend. It also allows other potential clients (e.g., a mobile app, other scripts) to consume the same data if needed in the future. Standard HTTP status codes and JSON error messages are used for clear communication.

### Total Energy Calculation Method

*   The `total_energy_kwh` value displayed on the statistics page is an *estimation*.
*   It's calculated using numerical integration, specifically the **Trapezoidal Rule**, within the `calculate_total_energy_kwh` function (`app/models.py`).
*   **How it works:**
    1.  Fetches all power readings (`power_watts`) and timestamps (`timestamp_unix`) for the device within the selected time range, sorted chronologically.
    2.  Iterates through consecutive pairs of readings `(time1, power1)` and `(time2, power2)`.
    3.  For each interval, it calculates the time difference (`time2 - time1` in seconds).
    4.  It calculates the average power during that interval `(power1 + power2) / 2`.
    5.  It estimates the energy for the interval as `average_power * time_difference` (in Watt-seconds or Joules).
    6.  It sums the energy calculated for all intervals.
    7.  Finally, it converts the total sum from Watt-seconds to kilowatt-hours (kWh) by dividing by 3,600,000.
*   This method provides a reasonable approximation of energy consumption based on discrete power measurements. The accuracy generally improves if the power readings are recorded more frequently and regularly. It requires at least two data points within the selected range to perform a calculation.

---


## Prerequisites

- **Python**: Version 3.7 or higher recommended.
- **pip**: Python package installer (usually included with Python).
- **SQLite Database**: An existing `power_data.db` file located in the `RPI` directory (one level above `WebServer`). This database should contain the `power_readings` table with the correct schema. The MQTT logger script (`RPI/MQTT/receive_mqtt_store_db.py`) or the test population scripts can create this.

---

## Installation & Setup

1.  **Clone the Repository** (if you haven't already):
    ```bash
    git clone <repository_url>
    cd EnergyMeter/RPI/WebServer/
    ```

2.  **Install Dependencies**:
    It's recommended to use a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install Flask
    ```
    (Flask is the primary dependency for this web server part).

3.  **Prepare the Database**:
    *   Ensure the `power_data.db` file exists in the `../` directory (relative to `WebServer`, i.e., in the `RPI` directory).
    *   If the database is empty or doesn't exist, you can run the MQTT logger script first or use a population script from the `Test/` directory to create the schema and add sample data:
        ```bash
        # Example using a population script:
        cd Test/
        python3 populate_week.py # Or populate_db.py
        cd ..
        ```

4.  **Verify Database Schema** (for reference):
    The `power_readings` table should have the following structure:
    ```sql
    CREATE TABLE IF NOT EXISTS power_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_device_id TEXT NOT NULL,
        source_device_id TEXT NOT NULL,
        timestamp_iso TEXT NOT NULL,
        timestamp_unix REAL, -- Storing as REAL for fractional seconds
        power_watts REAL NOT NULL,
        received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    -- Index for faster time-based lookups
    CREATE INDEX IF NOT EXISTS idx_timestamp_unix ON power_readings (timestamp_unix);
    ```

---

## Configuration

- **Database Path**: The path to `power_data.db` is determined relative to the application structure in `app/config.py`. It expects the database to be in the parent `RPI` directory.
- **Secret Key**: A default secret key is provided in `app/config.py` for development. For production deployments, it's crucial to set a strong, unique `SECRET_KEY` environment variable.
- **Environment Variables**: Flask uses environment variables for configuration:
    - `FLASK_APP=run.py`: Tells Flask which file to run (or `FLASK_APP=app` if using the factory directly). Set this before running `flask` commands.
    - `FLASK_ENV=development`: Enables debug mode, automatic reloading, and more verbose error pages. Use `development` for local work.
    - `FLASK_ENV=production`: Disables debug mode. **Use this for deployment.**
    - `SECRET_KEY`: (Optional for development, **Required for Production**) Sets the application's secret key.
    - `FLASK_RUN_HOST`: (Optional) Sets the host interface to bind to (e.g., `0.0.0.0` to allow external access). Default is `127.0.0.1`.
    - `FLASK_RUN_PORT`: (Optional) Sets the port to run on. Default is `5000`.

---

## Running the Application

1.  **Navigate to the Directory**:
    Make sure you are in the `EnergyMeter/RPI/WebServer/` directory in your terminal.

2.  **Activate Virtual Environment** (if used):
    ```bash
    source venv/bin/activate # Or venv\Scripts\activate on Windows
    ```

3.  **Set Environment Variables** (Bash example):
    ```bash
    export FLASK_APP=run.py
    export FLASK_ENV=development # Use 'production' for deployment
    # Optional: export SECRET_KEY='your_strong_secret_key_here' for production
    ```
    (On Windows, use `set FLASK_APP=run.py`, etc.)

4.  **Start the Flask Development Server**:
    ```bash
    # Run on localhost:5000 (default)
    flask run

    # Or run accessible on your network (replace 5000 with desired port if needed)
    flask run --host=0.0.0.0 --port=5000
    ```
    The server will indicate the address it's running on (e.g., `http://127.0.0.1:5000` or `http://0.0.0.0:5000`).

5.  **Access the Application**:
    Open your web browser and navigate to the address provided by the `flask run` command (e.g., `http://<your_raspberry_pi_ip>:5000` if running with `--host=0.0.0.0`, or `http://localhost:5000` if running locally).

---

## Usage

- **Dashboard (`/`)**: The landing page. Shows the count of active devices and status cards for all devices. Provides a quick overview of device activity, latest readings, and when data was last received. Click on a device card to navigate to its history page.
- **History (`/history`)**: Allows selecting a specific device and a time range (e.g., Last Hour, Last 24 Hours, Last 7 Days). Displays an interactive Plotly chart showing the power consumption trend for the selected period.
- **Statistics (`/statistics`)**: Allows selecting a device and time range. Calculates and displays key metrics: Average Power (Watts), Peak Usage (Watts and timestamp), and estimated Total Energy Consumption (kWh) for the selected period.

---

## API Endpoints

The application exposes several RESTful API endpoints under the `/api` prefix, primarily used by the frontend JavaScript.

- **`GET /api/data`**:
    - **Description**: Fetches the latest power reading (`latest`) and its Unix timestamp (`timestamp_unix`) for every distinct `source_device_id` found in the database.
    - **Response**: JSON object where keys are device IDs. Each device ID maps to an object containing `latest` (power in Watts) and `timestamp_unix`. Includes a special `Total` key which is currently unused on the frontend (previously held total power). Returns an `error` key on failure.
    ```json
    {
      "Device_A": {"latest": 150.25, "timestamp_unix": 1678886400.123},
      "Device_B": {"latest": 75.5, "timestamp_unix": 1678886395.456},
      "Total": {"total_power": 0.0}
    }
    ```

- **`GET /api/devices`**:
    - **Description**: Retrieves a list of all unique `source_device_id`s present in the `power_readings` table.
    - **Response**: JSON array of strings (device IDs).
    ```json
    ["Device_A", "Device_B", "Simulated_Device_C"]
    ```

- **`GET /api/historical_data`**:
    - **Description**: Gets historical power readings for a specific device over a specified time range.
    - **Query Parameters**:
        - `device_id` (required): The ID of the device.
        - `hours` (required): The number of hours back from the current time to fetch data for.
    - **Response**: JSON array of objects, each containing `timestamp` (ISO 8601 string with 'Z' timezone) and `power` (Watts). Sorted chronologically.
    ```json
    [
      {"timestamp": "2023-03-15T10:00:00.000Z", "power": 145.5},
      {"timestamp": "2023-03-15T10:01:00.000Z", "power": 148.2}
    ]
    ```

- **`GET /api/statistics`**:
    - **Description**: Calculates and returns statistics for a specific device over a specified time range.
    - **Query Parameters**:
        - `device_id` (required): The ID of the device.
        - `hours` (required): The number of hours back from the current time to calculate statistics for.
    - **Response**: JSON object containing calculated statistics. Values might be `null` if insufficient data exists.
    ```json
    {
      "device_id": "Device_A",
      "time_range_hours": 24,
      "average_power_watts": 125.67,
      "peak_usage": {
        "timestamp_unix": 1678850000.123,
        "timestamp_iso": "2023-03-14T22:13:20.123Z",
        "power": 310.5
      },
      "total_energy_kwh": 3.016
    }
    ```

- **`GET /health`**:
    - **Description**: A simple health check endpoint.
    - **Response**: Plain text "OK" with HTTP status 200.

---

## Testing Utilities

The `Test/` directory contains scripts useful for development and testing:

- **`populate_db.py`**: Initializes the database schema (if it doesn't exist) and inserts a small, fixed number of historical records for predefined devices. Good for initial setup.
- **`populate_week.py`**: Similar to `populate_db.py` but inserts data spanning approximately one week with a configurable interval, simulating more realistic historical data, including day/night variations.
- **`data_feeder.py`**: Simulates live devices sending data. Connects to the database and periodically inserts new random power readings for a set of devices using the current timestamp. Useful for testing the dashboard's dynamic updates and active status indicators.

Refer to `Test/README.md` for detailed usage instructions for these scripts.
