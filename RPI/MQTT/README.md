# MQTT to SQLite Database Logger (Serial Data)

This Python script (`receive_mqtt_store_db.py`) listens for messages published to a specific MQTT topic, parses the JSON payload (expected to contain power data originating from a serial source via an ESP8266), and stores the relevant information into an SQLite database file (`power_data.db`).

---

## Table of Contents

- [Purpose](#purpose)
- [How it Works](#how-it-works)
  - [Configuration](#configuration)
  - [Database Setup](#database-setup)
  - [MQTT Connection & Subscription](#mqtt-connection--subscription)
  - [Message Handling & Validation](#message-handling--validation)
  - [Database Insertion & ACID Compliance](#database-insertion--acid-compliance)
  - [Background Operation & Shutdown](#background-operation--shutdown)
- [Prerequisites & Setup](#prerequisites--setup)
- [Error Handling Scenarios](#error-handling-scenarios)
- [Checking the Stored Database](#checking-the-stored-database)
- [How to Run](#how-to-run)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Purpose

The primary goal of this script is to act as a persistent and reliable data logger for power readings sent over MQTT. It's designed to work in conjunction with an ESP8266 device (or similar) that reads data (e.g., from a serial port) and publishes it as JSON to an MQTT broker.

---

## How it Works

### Configuration

Key settings are defined as constants at the top of the script:

*   `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`: Address and port of the MQTT broker (e.g., Mosquitto).
*   `MQTT_TOPIC`: The specific topic the script subscribes to (e.g., `"sensors/power/serial"`).
*   `MQTT_CLIENT_ID`: A unique identifier for this script when connecting to the broker.
*   `MQTT_USER`, `MQTT_PASSWORD`: Credentials for MQTT broker authentication (if required). Leave as placeholders or blank if none.
*   `DATABASE_FILE`: The path to the SQLite database file. It's constructed to point to `power_data.db` in the parent directory (`RPI`).

### Database Setup (`setup_database` function)

1.  **Connection:** Connects to the SQLite database file specified by `DATABASE_FILE`. Creates the file if it doesn't exist. `check_same_thread=False` is used to allow the connection to be shared with the MQTT callback thread.
2.  **WAL Mode:** Enables Write-Ahead Logging (`PRAGMA journal_mode=WAL;`). This improves concurrency, allowing reads and writes to occur more simultaneously, which is beneficial if other applications (like the web server) might read the database while this script is writing.
3.  **Schema Creation:** Ensures the `power_readings` table exists with the correct structure:
    *   `id`: Auto-incrementing primary key.
    *   `reporter_device_id`: ID of the MQTT client publishing the message (e.g., ESP8266).
    *   `source_device_id`: ID of the actual device/sensor being measured.
    *   `timestamp_iso`: The timestamp string as received from the source.
    *   `timestamp_unix`: The timestamp converted to Unix epoch seconds (float), used for efficient sorting/filtering. Can be `NULL` if conversion fails.
    *   `power_watts`: The measured power value (float).
    *   `received_at`: Timestamp automatically added when the record is inserted by this script.
4.  **Indexing:** Ensures an index (`idx_timestamp_unix`) exists on the `timestamp_unix` column to speed up time-based queries.

### MQTT Connection & Subscription

1.  **Initialization:** Creates a Paho MQTT client instance.
2.  **Callbacks:** Assigns functions (`on_connect`, `on_message`, `on_disconnect`) to handle specific MQTT events.
3.  **Authentication:** Sets username/password if provided.
4.  **Connection:** Connects to the MQTT broker.
5.  **Subscription (`on_connect`):** Upon successful connection, the `on_connect` callback subscribes the client to the configured `MQTT_TOPIC`.

### Message Handling & Validation (`on_message` function)

1.  **Reception:** Triggered when a message arrives on the subscribed topic.
2.  **Decoding & Parsing:** Decodes the message payload from bytes to a UTF-8 string and parses it as JSON.
3.  **Extraction:** Safely extracts expected fields (`reporterDeviceId`, `sourceDeviceId`, `timestamp`, `power`) using `.get()`.
4.  **Validation:**
    *   Checks if all essential fields are present in the JSON payload.
    *   Verifies that the `power` value can be converted to a float.
    *   If validation fails, a warning is logged, and the message is skipped.
5.  **Timestamp Conversion (`parse_iso_to_unix`):** Attempts to convert the received `timestamp` string (expected ISO 8601 format) into a Unix epoch float. Handles 'Z' suffix for UTC and assumes UTC for naive datetimes. Returns `None` if parsing fails (e.g., if the source sent `millis()` instead).

### Database Insertion & ACID Compliance (`on_message` function)

1.  **Transaction:** Every `INSERT` operation is wrapped in an explicit SQL transaction (`BEGIN TRANSACTION` ... `COMMIT`).
2.  **Parameterized Query:** Uses `?` placeholders in the `INSERT` statement to prevent SQL injection vulnerabilities.
3.  **Commit/Rollback:**
    *   If the data is valid and the `INSERT` command executes successfully, `db_connection.commit()` makes the changes permanent in the database.
    *   If any `sqlite3.Error` occurs during the `INSERT` or `COMMIT` (e.g., disk full, constraint violation), the `except` block catches it, logs the error, and attempts to `db_connection.rollback()`. This discards any partial changes from the failed transaction, ensuring the database remains in a consistent state.

    **ACID Principles:**
    *   **Atomicity:** Guaranteed by the `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK` structure. The insertion is all or nothing.
    *   **Consistency:** Enforced by schema constraints (`NOT NULL`) and the script's pre-insertion validation. Rollback on error prevents inconsistent states.
    *   **Isolation:** Improved by WAL mode, allowing concurrent reads (e.g., by the web server) while this script writes, reducing lock contention.
    *   **Durability:** Ensured by SQLite's commit mechanism (especially with WAL). Once `commit()` succeeds, the changes are persistently stored and survive crashes or power failures.

### Background Operation & Shutdown

1.  **MQTT Loop:** `mqtt_client.loop_start()` runs the MQTT network operations (message handling, keep-alives, reconnections) in a background thread.
2.  **Main Thread:** The main script thread stays alive using `while True: time.sleep(1)`.
3.  **Graceful Shutdown (`signal_handler`):** Catches `SIGINT` (Ctrl+C) and `SIGTERM` signals. It cleanly stops the MQTT loop, disconnects from the broker, closes the database connection, and exits.

---

## Prerequisites & Setup

1.  **Python 3:** Ensure Python 3 is installed (`python3 --version`).
2.  **Paho MQTT Library:** Install using pip: `pip3 install paho-mqtt`.
3.  **MQTT Broker:** An MQTT broker (like Mosquitto) must be running and accessible from where the script runs. See the `MQTT/Test/README.md` for Mosquitto setup instructions if needed.
4.  **Database Location:** Ensure the parent directory (`RPI`) exists, as the script will create/use `power_data.db` there.

---

## Error Handling Scenarios

*   **MQTT Connection Issues:** Handled by Paho MQTT's auto-reconnect mechanism (`loop_start`). Errors during initial connection or authentication failures are logged.
*   **Network Loss:** The client attempts reconnection. Messages published during disconnection are typically lost for non-persistent sessions.
*   **Invalid Messages:** Non-JSON payloads, messages missing required fields, or messages with invalid data types (e.g., non-numeric power) are logged as warnings and skipped. Invalid timestamps result in `NULL` being stored for `timestamp_unix`.
*   **Database Errors:** Connection errors during setup cause the script to exit. Insertion errors trigger a transaction rollback and are logged.
*   **Power Loss:** Committed database transactions are durable due to SQLite's mechanisms (especially WAL). Data being processed but not yet committed at the time of power loss may be lost.

---

## Checking the Stored Database

You can view the contents of the `power_data.db` file using:

1.  **Command-line `sqlite3` tool:**
    ```bash
    sqlite3 ../power_data.db "SELECT * FROM power_readings ORDER BY id DESC LIMIT 10;"
    ```
2.  **The `print_power_db.py` script** located in the `MQTT/Test/` directory:
    ```bash
    python3 Test/print_power_db.py
    ```
    (Ensure the path in `print_power_db.py` points correctly to `../power_data.db`).
3.  **GUI Tools:** DB Browser for SQLite.

---

## How to Run

1.  **Configure:** Modify the constants at the top of `receive_mqtt_store_db.py` (Broker address, Topic, Credentials if needed).
2.  **Navigate:** Open a terminal and change to the `MQTT` directory:
    ```bash
    cd /path/to/EnergyMeter/RPI/MQTT/
    ```
3.  **Execute:** Run the script using Python 3:
    ```bash
    python3 receive_mqtt_store_db.py
    ```
4.  **Monitor:** The script will print connection status and log messages as they are received and stored.
5.  **Stop:** Press `Ctrl+C` to trigger the graceful shutdown process.

