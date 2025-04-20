# MQTT to SQLite Database Logger for Power Data

## Purpose

This Python script runs on a Raspberry Pi (or similar Linux system) and acts as an MQTT client. It subscribes to a specific MQTT topic where power data is being published (e.g., by an ESP8266 device). Upon receiving a message, it parses the JSON payload, validates the data, and stores it securely into an SQLite database file.

It's designed to be a reliable data logger for IoT sensor readings, incorporating error handling and ensuring data integrity using database transactions.

## Features

*   Connects to an MQTT broker.
*   Subscribes to a specified topic.
*   Receives JSON payloads.
*   Parses and validates incoming data.
*   Stores data into an SQLite database.
*   Uses database transactions (ACID principles) for reliable writes.
*   Handles potential JSON errors and database errors gracefully.
*   Includes graceful shutdown on receiving termination signals (Ctrl+C, SIGTERM).
*   Uses Write-Ahead Logging (WAL) for SQLite for improved concurrency and robustness.
*   Attempts to convert ISO8601 timestamps to Unix epoch for easier querying.

## Prerequisites & Setup on Raspberry Pi

1.  **Hardware:** Raspberry Pi 4 or similar device.
2.  **Operating System:** Raspberry Pi OS or another Linux distribution.
3.  **Python 3:** Should be pre-installed on most recent Raspberry Pi OS versions. Verify with `python3 --version`.
4.  **Install Paho MQTT Client Library:** Open a terminal and run:
    ```bash
    pip3 install paho-mqtt
    ```
5.  **Install and Run an MQTT Broker:** Mosquitto is highly recommended.
    *   Install Mosquitto:
        ```bash
        sudo apt update
        sudo apt install mosquitto mosquitto-clients -y
        ```
    *   Enable the Mosquitto service to start on boot:
        ```bash
        sudo systemctl enable mosquitto.service
        ```
    *   Start the Mosquitto service:
        ```bash
        sudo systemctl start mosquitto.service
        ```
    *   Verify it's running:
        ```bash
        sudo systemctl status mosquitto.service
        ```
    *   By default, Mosquitto runs on port 1883 without authentication. For production environments, consider configuring authentication by editing `/etc/mosquitto/mosquitto.conf` and `/etc/mosquitto/conf.d/`. This script currently assumes no authentication.
6.  **SQLite3:** The necessary Python `sqlite3` module is typically included with Python 3, so no separate installation is usually needed.

## Configuration

Modify the following constants in the `mqtt_data_to_db.py` script as needed:

*   `MQTT_BROKER_HOST`: IP address or hostname of your MQTT broker. Defaults to `"localhost"` if the broker is running on the same Raspberry Pi.
*   `MQTT_BROKER_PORT`: Port number for the MQTT broker. Defaults to `1883`.
*   `MQTT_TOPIC`: The MQTT topic to subscribe to. **This must match the topic the ESP8266 is publishing to** (e.g., `"sensors/power/dummy"`).
*   `MQTT_CLIENT_ID`: A unique identifier for this Python script when connecting to the broker. Defaults to `"rpi-db-logger"`.
*   `DATABASE_FILE`: The name (and optionally path) for the SQLite database file where data will be stored. Defaults to `"power_data.db"`.

## Functionality Explained

### MQTT Broker, Client, and Server Roles

MQTT uses a publish/subscribe architecture, which relies on three main components:

1.  **Broker (Server):** This is the central hub responsible for managing the flow of messages. In this setup, the Mosquitto service running on the Raspberry Pi acts as the MQTT Broker/Server. It receives messages published by clients and distributes them to clients that have subscribed to the relevant topics. The broker doesn't typically inspect or modify the message content.
2.  **Client (Publisher):** A client that connects to the broker and sends (publishes) messages to specific topics. In your project, the ESP8266 running `dummy_data_send_mqtt.ino` is an MQTT client acting as a publisher.
3.  **Client (Subscriber):** A client that connects to the broker and registers interest (subscribes) in receiving messages published to specific topics. This Python script (`mqtt_data_to_db.py`) is an MQTT client acting as a subscriber.

The broker decouples publishers from subscribers; they don't need to know about each other's existence or IP addresses. They only need to know the address of the broker and agree on the topics to use.

### Connection Workflow

1.  The Python script starts and connects to the MQTT broker specified by `MQTT_BROKER_HOST` and `MQTT_BROKER_PORT`.
2.  Upon successful connection, the `on_connect` callback is triggered, and the script subscribes to the `MQTT_TOPIC`.
3.  The ESP8266 (running separately) connects to the *same* MQTT broker and periodically publishes JSON messages to the `MQTT_TOPIC`.
4.  The MQTT broker receives the message from the ESP8266.
5.  Because the Python script is subscribed to that topic, the broker forwards the message to the script.
6.  The Paho MQTT library triggers the `on_message` callback in the Python script, passing the received message.

### Database: Schema and Storage

The script uses SQLite, a lightweight, file-based relational database.

*   **Connection:** It connects to the file specified by `DATABASE_FILE`. If the file doesn't exist, it's created automatically.
*   **Write-Ahead Logging (WAL):** `PRAGMA journal_mode=WAL;` is enabled. This mode generally provides better performance and concurrency compared to the default rollback journal, especially beneficial if other processes might read the database while this script is writing to it. It also contributes to durability.
*   **Schema (`power_readings` table):**
    *   `id` (INTEGER PRIMARY KEY AUTOINCREMENT): A unique, auto-incrementing number for each record. Standard practice for primary keys.
    *   `reporter_device_id` (TEXT NOT NULL): Stores the `mqtt_client_id` of the ESP8266 that sent the data. Useful if multiple ESPs report to the same topic. Stored as TEXT (string). `NOT NULL` ensures this field is always present.
    *   `source_device_id` (TEXT NOT NULL): Stores the ID of the specific load/sensor the data pertains to (e.g., "DummyLoad_A"). Allows filtering data by the source device. Stored as TEXT. `NOT NULL`.
    *   `timestamp_iso` (TEXT NOT NULL): Stores the original timestamp string exactly as received from the ESP8266. This is important for preserving the raw data, especially since the ESP might send `millis()` as a fallback if NTP fails. Stored as TEXT. `NOT NULL`.
    *   `timestamp_unix` (REAL): Stores the timestamp converted into Unix epoch seconds (a floating-point number). This format is ideal for efficient database queries involving time ranges (e.g., "get all readings from the last hour"). It's stored as REAL (float). This field can be `NULL` if the `timestamp_iso` string wasn't a valid ISO8601 format (like the `millis()` fallback). An index is created on this column (`idx_timestamp_unix`) to significantly speed up queries that filter or sort by time.
    *   `power_watts` (REAL NOT NULL): Stores the received power reading. Stored as REAL to accommodate decimal values. `NOT NULL`.
    *   `received_at` (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP): Automatically records the date and time when the Python script inserted the record into the database. Useful for monitoring processing latency or diagnosing data gaps.

### Data Processing and Validation

Inside the `on_message` callback:

1.  The raw message payload (bytes) is decoded into a UTF-8 string.
2.  The string is parsed as JSON using `json.loads()`.
3.  Essential fields (`reporterDeviceId`, `sourceDeviceId`, `timestamp`, `power`) are extracted using `.get()` to avoid errors if a field is missing.
4.  A validation check ensures all required fields were found.
5.  The `power` value is validated to ensure it can be converted to a floating-point number.
6.  `parse_iso_to_unix` attempts to convert the `timestamp` string into a Unix timestamp.
7.  If validation passes, the data is prepared for database insertion.

### Error Handling and Failure Management

The script incorporates several layers of error handling:

1.  **MQTT Connection Errors:** The Paho MQTT client library (`loop_start()`) handles automatic reconnection attempts if the connection to the broker drops unexpectedly. The `on_disconnect` callback logs these events.
2.  **Invalid Message Format:**
    *   If a message payload is not valid JSON, a `json.JSONDecodeError` is caught, a warning is logged, and the message is skipped.
    *   If a JSON message is missing required fields or has an invalid `power` value, the validation checks catch this, log a warning, and skip the message.
3.  **Database Write Failures (ACID Compliance):**
    *   **Transactions:** Every `INSERT` operation is wrapped in an explicit SQL transaction (`BEGIN TRANSACTION` ... `COMMIT`).
    *   **Atomicity:** This ensures that the `INSERT` operation is atomic – it either completes successfully in its entirety, or if any error occurs before the `COMMIT`, it has no effect on the database.
    *   **Consistency:** By rolling back failed transactions and using `NOT NULL` constraints, the script helps maintain database consistency.
    *   **Isolation:** WAL mode improves isolation, allowing reads and writes to occur more concurrently. `check_same_thread=False` is necessary as the `on_message` callback runs in a separate thread.
    *   **Durability:** SQLite's WAL mechanism ensures that once a `COMMIT` is successful, the changes are durable and will survive application crashes or system power failures. If a crash occurs *during* a commit, SQLite automatically recovers the database to a consistent state upon the next connection.
    *   **Error Handling:** If an `sqlite3.Error` occurs during the `INSERT` or `COMMIT` (e.g., disk full, permission error), the `except` block catches it, logs the error, and attempts to `ROLLBACK` the transaction, preventing partial data writes.
4.  **Graceful Shutdown:** The script listens for `SIGINT` (Ctrl+C) and `SIGTERM` signals. When received, the `signal_handler` function:
    *   Stops the MQTT client's network loop (`loop_stop`).
    *   Disconnects the MQTT client gracefully (`disconnect`).
    *   Closes the SQLite database connection (`db_connection.close()`).
    *   Exits the script cleanly (`sys.exit(0)`). This prevents abrupt termination that could potentially leave resources open or cause issues.

## How to Run

1.  Ensure all prerequisites listed above are installed and the MQTT broker (Mosquitto) is running.
2.  Save the Python code as `mqtt_data_to_db.py` on your Raspberry Pi.
3.  Modify the configuration constants at the top of the script if necessary (e.g., `MQTT_BROKER_HOST`, `MQTT_TOPIC`).
4.  Open a terminal on your Raspberry Pi.
5.  Navigate to the directory where you saved the file.
6.  Run the script using Python 3:
    ```bash
    python3 mqtt_data_to_db.py
    ```
7.  The script will print status messages indicating connection to the database and MQTT broker, and then log messages as they are received and stored.
8.  To stop the script, press `Ctrl+C` in the terminal. The script should print shutdown messages as it disconnects and closes resources gracefully.

You can then use tools like `sqlite3` command-line interface (`sqlite3 power_data.db`) or graphical tools like DB Browser for SQLite to inspect the data stored in the `power_data.db` file.
