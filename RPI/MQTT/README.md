# MQTT to SQLite Database Logger (Serial Data)

This Python script listens for messages published to a specific MQTT topic, parses the JSON payload (expected to contain power data originating from a serial source via an ESP8266), and stores the relevant information into an SQLite database file.

## Purpose

The primary goal of this script is to act as a persistent data logger for power readings sent over MQTT. It's designed to work in conjunction with an ESP8266 device running firmware like `receive_data_send_mqtt.ino`, which reads data from a serial port and publishes it.

## How it Works

1.  **Configuration:** Key settings like the MQTT broker address, port, topic to subscribe to, MQTT credentials, and the database filename are defined as constants at the top of the script.
2.  **Database Setup (`setup_database`):**
    *   Connects to the specified SQLite database file (`power_data.db` by default). If the file doesn't exist, it's created.
    *   Uses `check_same_thread=False` to allow the database connection to be used by the MQTT callback thread.
    *   Enables **Write-Ahead Logging (WAL)** mode (`PRAGMA journal_mode=WAL;`). This improves concurrency by allowing reads and writes to happen simultaneously, reducing locking contention.
    *   Ensures the `power_readings` table exists with the correct schema (columns for reporter/source device IDs, timestamps, power value, and received time).
    *   Ensures an index exists on the `timestamp_unix` column for efficient querying based on time.
3.  **MQTT Connection:**
    *   Initializes the Paho MQTT client with a unique `MQTT_CLIENT_ID`.
    *   Assigns callback functions (`on_connect`, `on_message`, `on_disconnect`) to handle MQTT events.
    *   Sets the username and password for broker authentication if they are provided in the configuration.
    *   Attempts to connect to the MQTT broker specified by `MQTT_BROKER_HOST` and `MQTT_BROKER_PORT`.
4.  **Subscription (`on_connect`):** Upon successfully connecting to the broker, the `on_connect` callback is triggered, and the script subscribes to the configured `MQTT_TOPIC`.
5.  **Message Handling (`on_message`):**
    *   When a message arrives on the subscribed topic, the `on_message` callback is executed.
    *   The message payload (expected to be bytes) is decoded into a UTF-8 string.
    *   The string is parsed as JSON into a Python dictionary.
    *   Relevant fields (`reporterDeviceId`, `sourceDeviceId`, `timestamp`, `power`) are extracted using `.get()` for safety against missing keys.
    *   **Validation:** Checks if essential fields are present and if the `power` value can be converted to a float. If validation fails, a warning is printed, and the message is skipped.
    *   **Timestamp Conversion:** Attempts to parse the `timestamp` string (expected ISO 8601 format like `YYYY-MM-DDTHH:MM:SSZ`) into a Unix epoch timestamp (float) using `parse_iso_to_unix`. If parsing fails (e.g., the ESP8266 sent `millis()` as a fallback), the `timestamp_unix` field will be stored as `NULL` in the database.
    *   **Database Insertion:**
        *   Uses an explicit database transaction (`BEGIN TRANSACTION` ... `COMMIT`). This ensures that the insertion is **atomic** (either fully completes or doesn't happen at all).
        *   Inserts the extracted and processed data into the `power_readings` table using a parameterized query (`?`) to prevent SQL injection vulnerabilities.
        *   If the insertion is successful, the transaction is committed, making the changes permanent.
        *   If any error occurs during insertion, the transaction is rolled back, discarding any partial changes from that transaction.
        
        **ACID Principles in Action:**

        The script leverages SQLite's features to adhere to ACID principles for database operations:
        *   **Atomicity:** Ensured by wrapping the `INSERT` statement within `BEGIN TRANSACTION` and `COMMIT`. If any part of the insertion fails (e.g., due to constraints or errors), the `except` block triggers a `ROLLBACK`, guaranteeing that the database is either fully updated with the new row or remains completely unchanged by that attempt. The operation is treated as a single, indivisible unit.
        *   **Consistency:** Primarily maintained by the database schema (`NOT NULL` constraints) and the script's validation logic. The script checks for required fields and valid data types before attempting the `INSERT`. If an operation would violate a database constraint (like inserting `NULL` into a `NOT NULL` column), SQLite prevents it, and the transaction rollback ensures the database remains in a valid state according to its rules.
        *   **Isolation:** Achieved through SQLite's transaction mechanism and enhanced by the use of **Write-Ahead Logging (WAL)** mode (`PRAGMA journal_mode=WAL;`). WAL allows read operations to occur concurrently with write operations, reducing lock contention and improving performance compared to the default rollback journal. While SQLite's default isolation levels handle concurrency, WAL makes it more efficient in scenarios with frequent writes (like this logger) and potential reads (like querying the data).
        *   **Durability:** Guaranteed by SQLite once the `COMMIT` command returns successfully. SQLite ensures that committed data is written to persistent storage (first to the WAL file, then checkpointed to the main database file) in a way that survives system crashes or power failures. Even if power is lost during the commit process, SQLite's recovery mechanisms ensure the database can be restored to the last consistent state upon restart.

6.  **Background Loop:** `mqtt_client.loop_start()` runs the MQTT network communication (handling keep-alives, message reception, automatic reconnection attempts) in a separate background thread. The main thread simply sleeps, keeping the script alive.
7.  **Graceful Shutdown (`signal_handler`):** The script listens for `SIGINT` (Ctrl+C) and `SIGTERM` signals. When received, it stops the MQTT loop, disconnects cleanly from the broker, and closes the database connection before exiting.

## Error Handling Scenarios

*   **MQTT Broker Unreachable (Initial Connect):** If the script cannot connect to the broker on startup (wrong address, port, or broker is down), it prints an error and exits.
*   **MQTT Authentication Failure:** If the `MQTT_USER` and `MQTT_PASSWORD` are incorrect, the `on_connect` callback will report `rc=5` (Authentication Error), and the script will likely fail to subscribe or receive messages. The Paho client might keep retrying the connection.
*   **Network Loss / MQTT Disconnection:**
    *   If the network connection to the broker is lost after initial connection, the `on_disconnect` callback will be triggered with a non-zero return code.
    *   The Paho MQTT client (`loop_start()`) automatically attempts to reconnect in the background with exponential backoff.
    *   **Messages published to the topic while the script is disconnected are lost**; MQTT brokers typically do not queue messages for non-cleanly disconnected, non-persistent clients.
*   **Invalid MQTT Message Payload:**
    *   **Non-JSON:** If the received payload is not valid JSON, a `json.JSONDecodeError` is caught, a warning is printed, and the message is ignored.
    *   **Missing Fields:** If the JSON is valid but missing required fields (`reporterDeviceId`, `sourceDeviceId`, `timestamp`, `power`), the validation check fails, a warning is printed, and the message is ignored.
    *   **Invalid Power Value:** If the `power` field cannot be converted to a float, a warning is printed, and the message is ignored.
    *   **Invalid Timestamp:** If the `timestamp` string is not a valid ISO 8601 format, `parse_iso_to_unix` returns `None`. A message is printed, and `NULL` is stored in the `timestamp_unix` database column, but the rest of the data is still saved.
*   **Database Errors:**
    *   **Connection Failure:** If the database file cannot be opened or created during `setup_database` (e.g., permissions issue), the script prints an error and exits.
    *   **Insertion Failure:** If an error occurs during `INSERT` (e.g., disk full, database corruption), the `sqlite3.Error` is caught. The script attempts to `rollback()` the transaction, ensuring the database remains in a consistent state prior to the failed insertion attempt. An error message is printed.
*   **Power Loss (Raspberry Pi):**
    *   **Data in Transit:** Any MQTT message being processed when power is lost might be lost if it hasn't been fully committed to the database.
    *   **Database Integrity:** SQLite's **WAL (Write-Ahead Logging)** mode and **transaction mechanism** are designed for durability. When a transaction is successfully committed, the data is written first to the WAL file and then checkpointed to the main database file. This process ensures that even if power is lost during a write, the database can recover to the last fully committed state upon restart, preventing corruption. Data from *committed* transactions should survive a power outage.

## Checking the Stored Database

You can easily view the contents of the SQLite database using the companion script `print_power_db.py`.

1.  **Ensure `print_power_db.py` is present** in the same directory or accessible in your Python path.
2.  **Make sure the `DATABASE_FILE` constant** inside `print_power_db.py` matches the one used by `receive_mqtt_store_db.py` (default is `power_data.db`).
3.  **Run the script** from your terminal:
    ```bash
    python print_power_db.py
    ```
4.  **Output:** The script will connect to the database file, fetch all rows from the `power_readings` table, and print them to the console in a formatted table, including headers. This allows you to verify the data being logged by `receive_mqtt_store_db.py`.

