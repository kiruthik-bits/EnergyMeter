# Energy Monitoring Web Server

A Flask-based web application for visualizing energy consumption data from IoT devices stored in an SQLite database.

---

## Features

- **Dashboard**: Displays the latest power readings, total power, data freshness indicators, and clickable device cards linking to historical data. Includes auto-refresh and manual refresh options.
- **Historical Data Visualization**: Interactive charts (via Plotly.js) for power usage trends over various time ranges (1 hour to 30 days).
- **Device Statistics**: Key metrics like average power, peak usage, and total energy consumption (kWh) for selected devices.
- **Modular Design**: Organized using Flask Blueprints and an application factory pattern.
- **Dynamic Updates**: Uses JavaScript (`fetch` API) and RESTful APIs for seamless updates.
- **Responsive UI**: Built with Bootstrap 5 for a clean and adaptive interface.

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
  - `base.html`: Base layout with Bootstrap.
  - `index.html`: Dashboard page.
  - `history.html`: Historical data visualization.
  - `statistics.html`: Device statistics.
- **Static Files**:
  - `css/style.css`: Custom CSS.
  - `js/dashboard.js`: Dashboard logic.
  - `js/history.js`: Historical data visualization.
  - `js/statistics.js`: Statistics calculations.

### Database

- **`power_data.db`**: SQLite database containing the `power_readings` table.

### Testing Utilities

- **`Test/`**: Scripts for populating and simulating database data.

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
*   The database schema is kept straightforward, focusing on storing the core power readings efficiently.

### Frontend Technology (Bootstrap, Plotly.js, Vanilla JS)

*   **Bootstrap 5:** Used for the overall UI layout, styling, and responsiveness. It provides pre-built components (cards, navigation, grid system) that accelerate frontend development and ensure a consistent, modern look across different screen sizes.
*   **Plotly.js:** Chosen for rendering interactive charts on the history page. It offers good interactivity (zooming, panning, hover details) and handles date/time axes well, making it suitable for time-series data visualization. It replaced Chart.js to potentially address rendering issues and offer enhanced interactivity.
*   **Vanilla JavaScript (with Fetch API):** Standard browser JavaScript is used for frontend logic. The `fetch` API is employed to make asynchronous requests to the backend API endpoints, allowing pages (like the dashboard and statistics) to update dynamically without requiring full page reloads. This provides a smoother user experience.

### API Design (RESTful)

*   A separate API (using the `/api` blueprint) is implemented to provide data to the frontend JavaScript.
*   This follows RESTful principles, where specific endpoints are responsible for specific data resources (e.g., `/api/devices`, `/api/historical_data`).
*   This **decoupling** means the backend can be developed and tested independently of the frontend. It also allows other potential clients (e.g., a mobile app, other scripts) to consume the same data if needed in the future.

### Total Energy Calculation Method

*   The `total_energy_kwh` value displayed on the statistics page is an *estimation*.
*   It's calculated using numerical integration, specifically the **Trapezoidal Rule**, within the `calculate_total_energy_kwh` function (`app/models.py`).
*   **How it works:**
    1.  Fetches all power readings (`power_watts`) and timestamps (`timestamp_unix`) for the device within the selected time range, sorted chronologically.
    2.  Iterates through consecutive pairs of readings `(time1, power1)` and `(time2, power2)`.
    3.  For each interval, it calculates the time difference (`time2 - time1` in seconds).
    4.  It calculates the average power during that interval `(power1 + power2) / 2`.
    5.  It estimates the energy for the interval as `average_power * time_difference` (in Watt-seconds).
    6.  It sums the energy calculated for all intervals.
    7.  Finally, it converts the total sum from Watt-seconds to kilowatt-hours (kWh) by dividing by 3,600,000.
*   This method provides a reasonable approximation of energy consumption based on discrete power measurements. The accuracy generally improves if the power readings are recorded more frequently.

---


## Prerequisites

- **Python**: Version 3.7 or higher.
- **pip**: Python package installer.
- **Flask**: Install via `pip install Flask`.
- **SQLite**: Ensure `power_data.db` exists with the correct schema.

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd EnergyMeter/RPI/WebServer/
   ```

2. **Install Dependencies**:
   ```bash
   pip install Flask
   ```

3. **Prepare the Database**:
   - Ensure `power_data.db` exists in the `../` directory.
   - Run a population script if needed:
     ```bash
     cd Test/
     python populate_week.py
     cd ..
     ```

4. **Verify Database Schema**:
   ```sql
   CREATE TABLE power_readings (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       reporter_device_id TEXT NOT NULL,
       source_device_id TEXT NOT NULL,
       timestamp_iso TEXT NOT NULL,
       timestamp_unix REAL,
       power_watts REAL NOT NULL,
       received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   CREATE INDEX idx_timestamp_unix ON power_readings (timestamp_unix);
   ```

---

## Configuration

- **Database Path**: Defined in `app/config.py` as `../power_data.db`.
- **Environment Variables**:
  - `FLASK_APP=run.py`
  - `FLASK_ENV=development` (for development) or `FLASK_ENV=production` (for deployment).
  - `SECRET_KEY`: Override for production.
  - Optional: `FLASK_RUN_HOST`, `FLASK_RUN_PORT`.

---

## Running the Application

1. **Set Environment Variables**:
   ```bash
   export FLASK_APP=run.py
   export FLASK_ENV=development
   ```

2. **Start the Server**:
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

3. **Access the Application**:
   Open `http://<your_rpi_ip_address>:5000` in a browser.

---

## Usage

- **Dashboard (`/`)**: View current power readings and device statuses. Click cards for history.
- **History (`/history`)**: Select a device and time range to view power trends.
- **Statistics (`/statistics`)**: View calculated metrics for selected devices.

---

## API Endpoints

- **`GET /api/data`**: Latest power readings and total power.
- **`GET /api/devices`**: List of devices.
- **`GET /api/historical_data`**: Historical data for a device and time range.
- **`GET /api/statistics`**: Calculated statistics for a device and time range.
- **`GET /health`**: Health check endpoint.

---

## Testing Utilities

- **`populate_db.py`**: Creates schema and inserts sample data.
- **`populate_week.py`**: Inserts ~1 week of data.
- **`data_feeder.py`**: Simulates live data insertion.

For more details, see `Test/README.md`.
