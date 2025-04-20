# ESP8266 Dummy Power Data MQTT Publisher (Batch Mode)

## Purpose

This Arduino sketch runs on an ESP8266 microcontroller. It simulates power readings for multiple predefined dummy devices and publishes this data to an MQTT broker at regular intervals. Each interval, it sends data for *all* configured dummy devices consecutively as a batch. It uses NTP (Network Time Protocol) to get accurate timestamps for the data.

This is useful for testing MQTT brokers, data ingestion pipelines, or dashboard setups without needing actual sensor hardware connected.

## Hardware Requirements

*   An ESP8266-based board (e.g., NodeMCU, Wemos D1 Mini)
*   A WiFi network with internet access (for WiFi connection and NTP)
*   Access to an MQTT Broker

## Software Dependencies

This sketch requires the following Arduino libraries:

*   **ESP8266WiFi**: For connecting the ESP8266 to WiFi. (Usually included with ESP8266 board support)
*   **PubSubClient**: An MQTT client library for Arduino. (Install via Arduino Library Manager)
*   **ArduinoJson**: For creating JSON payloads. (Install via Arduino Library Manager - Use v6 or later)
*   **NTPClient**: For fetching time from NTP servers. (Install via Arduino Library Manager)
*   **WiFiUdp**: Used by NTPClient for UDP communication. (Usually included with ESP8266 board support)

## Configuration

Before uploading the sketch, you need to configure the settings near the top of the `dummy_data_send_mqtt.ino` file. These are defined using C preprocessor macros (`#define`), often wrapped in `#ifndef` guards. This allows you to set default values in the code but also potentially override them using build flags (e.g., in PlatformIO's `platformio.ini`) without modifying the source file directly.

1.  **WiFi Credentials:**
    *   `WIFI_SSID`: Your WiFi network name (SSID).
      ```cpp
      #ifndef WIFI_SSID
      #define WIFI_SSID "YourWifiNetworkName"
      #endif
      ```
    *   `WIFI_PASSWORD`: Your WiFi password.
      ```cpp
      #ifndef WIFI_PASSWORD
      #define WIFI_PASSWORD "YourWifiPassword"
      #endif
      ```

2.  **MQTT Broker Details:**
    *   `MQTT_SERVER`: The IP address or hostname of your MQTT broker.
      ```cpp
      #ifndef MQTT_SERVER
      #define MQTT_SERVER "192.168.1.100" // Or "mqtt.example.com"
      #endif
      ```
    *   `MQTT_PORT`: The port your MQTT broker is listening on (typically `1883` for non-TLS MQTT, `8883` for TLS/MQTTS).
      ```cpp
      #ifndef MQTT_PORT
      #define MQTT_PORT 1883
      #endif
      ```
    *   `MQTT_USER`: The username for MQTT authentication (leave empty `""` if none).
      ```cpp
      #ifndef MQTT_USER
      #define MQTT_USER "your_mqtt_username" // Or ""
      #endif
      ```
    *   `MQTT_PASSWORD`: The password for MQTT authentication (leave empty `""` if none).
      ```cpp
      #ifndef MQTT_PASSWORD
      #define MQTT_PASSWORD "your_mqtt_password" // Or ""
      #endif
      ```
    *   `MQTT_CLIENT_ID`: A unique identifier for this ESP8266 client. Must be unique among all clients connecting to the broker.
      ```cpp
      #ifndef MQTT_CLIENT_ID
      #define MQTT_CLIENT_ID "esp8266-dummy-sender-01"
      #endif
      ```
    *   `MQTT_TOPIC`: The MQTT topic where the dummy data will be published.
      ```cpp
      #ifndef MQTT_TOPIC
      #define MQTT_TOPIC "sensors/power/dummy"
      #endif
      ```

3.  **NTP Configuration:**
    *   `NTP_SERVER`: The NTP server to use (default is `pool.ntp.org`).
      ```cpp
      #define NTP_SERVER "pool.ntp.org"
      ```
    *   `UTC_OFFSET_SECONDS`: Your timezone offset from UTC in seconds (e.g., IST is UTC+5:30 = `19800`).
      ```cpp
      #define UTC_OFFSET_SECONDS 19800
      ```
    *   `NTP_UPDATE_INTERVAL_MS`: How often to attempt an NTP time sync (in milliseconds).
      ```cpp
      #define NTP_UPDATE_INTERVAL_MS (60 * 1000) // 60 seconds
      ```

4.  **Dummy Data Configuration:**
    *   `DUMMY_DATA_INTERVAL_MS`: The interval (in milliseconds) between sending batches of data (e.g., `60000` for 1 minute).
      ```cpp
      #define DUMMY_DATA_INTERVAL_MS (60 * 1000)
      ```
    *   `DELAY_BETWEEN_MESSAGES_MS`: A small delay (in milliseconds) introduced between sending messages for each device within a single batch (e.g., `50`).
      ```cpp
      #define DELAY_BETWEEN_MESSAGES_MS 50
      ```
    *   `dummyDeviceIds`: An array of C-style strings defining the names of the simulated devices. Note: This is still a `const char*` array, not a macro itself, but it's part of the configuration.
      ```cpp
      const char* dummyDeviceIds[] = {"DummyLoad_A", "DummyLoad_B", "DummyLoad_C"};
      ```

5.  **MQTT Retry Configuration:**
    *   `MAX_RETRY_DELAY_MS`: Maximum delay between MQTT publish retries (milliseconds).
      ```cpp
      #define MAX_RETRY_DELAY_MS 60000 // 60 seconds
      ```
    *   `INITIAL_RETRY_DELAY_MS`: Initial delay before the first retry attempt (milliseconds).
      ```cpp
      #define INITIAL_RETRY_DELAY_MS 5000 // 5 seconds
      ```


## Functionality Explained

### WiFi Connection (`setupWiFi` function)

1.  **Mode:** The ESP8266 is set to Station mode (`WIFI_STA`), meaning it will connect to an existing WiFi network.
2.  **Begin Connection:** `WiFi.begin(ssid, password)` starts the connection process using the configured credentials.
3.  **Wait & Check:** The code enters a `while` loop that repeatedly checks the connection status (`WiFi.status()`) . It prints dots (`.`) to the Serial Monitor while waiting.
4.  **Timeout:** The loop attempts connection for a limited number of tries (controlled by `attempts < 30` with a 500ms delay, roughly 15 seconds).
5.  **Success:** If `WiFi.status()` becomes `WL_CONNECTED`, it prints the connection success message and the IP address assigned to the ESP8266.
6.  **Failure:** If the connection fails after the attempts, it prints an error message and restarts the ESP8266 (`ESP.restart()`) to try again.

### MQTT Operation

1.  **Client Initialization:** A `PubSubClient` object is created, associated with the `WiFiClient`.
2.  **Server Configuration:** `client.setServer()` tells the client the address and port of the MQTT broker.
3.  **Connection (`connectMQTT` function):**
    *   This function is called when the client is not connected (`!client.connected()`).
    *   It attempts to connect to the broker using `client.connect()`, providing the `mqtt_client_id` and optionally the username/password.
    *   If the connection fails, it prints an error code (`client.state()`) and waits 5 seconds before retrying. This is a *blocking* wait in the current implementation.
    *   On successful connection, retry parameters are reset.
4.  **Main Loop (`handleMQTT` and `client.loop()`):**
    *   `handleMQTT()` first checks for WiFi connection.
    *   If MQTT is disconnected, it calls `connectMQTT()`.
    *   Crucially, `client.loop()` is called in `handleMQTT()`. This function must be called regularly. It handles:
        *   Reading incoming messages (if subscribed to topics).
        *   Processing MQTT keep-alive pings to maintain the connection.
        *   Managing the outgoing message queue.
5.  **Publishing (`generateAndPublishDummyDataBatch` -> `publishData`):**
    *   The `generateAndPublishDummyDataBatch` function iterates through the `dummyDeviceIds`.
    *   For each device, it creates a JSON payload using `ArduinoJson`.
    *   It calls `publishData()` with the JSON payload.
    *   `publishData()` checks the MQTT connection status.
    *   It uses `client.publish(mqtt_topic, payload)` to send the message to the broker on the specified topic.
6.  **Retry Logic (`publishData` and `handleMQTT`):**
    *   If `client.publish()` fails (returns `false`), `publishData()` checks if another retry is already pending (`!retryPending`).
    *   If no retry is pending, it copies the failed payload into `pendingRetryMessage.payload`, sets `retryPending = true`, and records the failure time.
    *   The `handleMQTT()` function checks if `retryPending` is true and if enough time (`currentRetryDelay`) has passed since the last attempt.
    *   If conditions are met, it calls `publishData()` again with the stored payload.
    *   If the retry fails, the `currentRetryDelay` is increased (exponential backoff) up to `MAX_RETRY_DELAY_MS`.
    *   If the retry succeeds, `retryPending` is cleared.
    *   **Note:** This simple retry logic only stores *one* failed message at a time. If multiple messages fail within a batch before a retry occurs, only the first one that failed will be queued.

### NTP Time Synchronization

1.  **Client Initialization:** A `NTPClient` object is created, linked to a `WiFiUDP` object and configured with the NTP server address and timezone offset. The last argument (`60 * 60 * 1000`) is the default update interval *within the library*, but we also manage updates manually.
2.  **Begin:** `timeClient.begin()` is called in `setup()` after WiFi connects.
3.  **Periodic Update (`loop`):** The main `loop` checks a timer (`lastNtpUpdateTime`). Every `ntpUpdateInterval` (e.g., 60 seconds), it calls `timeClient.update()`. This is a non-blocking call that attempts to fetch the latest time from the NTP server. Success or failure is printed.
4.  **Getting Timestamp (`getNTPTimestamp`):**
    *   This function is called just before publishing data.
    *   It calls `timeClient.getEpochTime()` to get the number of seconds since Jan 1, 1970, based on the last successful sync.
    *   It checks if the epoch time seems valid (e.g., greater than a known date like Jan 1, 2023) to infer if NTP has synchronized at least once.
    *   If valid, it returns the formatted time string (ISO 8601 format like `YYYY-MM-DDTHH:MM:SSZ`) using `timeClient.getFormattedTime()`.
    *   If not valid (NTP hasn't synced yet), it returns the device's uptime (`millis()`) as a fallback string.

### Dummy Data Generation (`generateAndPublishDummyDataBatch`)

1.  **Trigger:** This function is called from the main `loop()` whenever the `DUMMY_DATA_INTERVAL_MS` timer expires.
2.  **Iteration:** It loops through the `dummyDeviceIds` array.
3.  **Value Generation:** Inside the loop, for each device ID, it generates a random floating-point number (`dummyPower`) within a specified range using `random()`.
4.  **JSON Creation:** It creates a `StaticJsonDocument` and populates it with:
    *   `reporterDeviceId`: The `mqtt_client_id` of this ESP8266.
    *   `sourceDeviceId`: The current dummy device ID from the loop.
    *   `timestamp`: Fetched using `getNTPTimestamp()`.
    *   `power`: The randomly generated `dummyPower` value.
5.  **Serialization & Publishing:** The JSON document is serialized into a character buffer (`jsonBuffer`), and then `publishData()` is called to send it.
6.  **Delay:** A small `delay(DELAY_BETWEEN_MESSAGES_MS)` and `yield()` are called after each message within the batch to allow processing time and maintain WiFi stability.

## Arduino <-> ESP8266 Connections

**This specific sketch (`dummy_data_send_mqtt.ino`) does NOT require any connection to an Arduino.** It generates the power data internally within the ESP8266 itself.

However, the related sketch (`receive_data_send_mqtt.ino`) *is* designed to receive data from an Arduino (or another device) via Serial communication. For that setup, the connections would typically be:

*   **ESP8266 RX (GPIO3) <--> Arduino TX (Pin 1)**
*   **ESP8266 GND <--> Arduino GND**

**Important:** The grounds (GND) of both devices *must* be connected for serial communication to work reliably. Also, ensure the `SERIAL_BAUD_RATE` constant in both the Arduino sending sketch and the ESP8266 receiving sketch match.

## How MQTT Works (Briefly)

MQTT (Message Queuing Telemetry Transport) is a lightweight publish/subscribe messaging protocol, ideal for IoT devices and constrained networks.

*   **Publish/Subscribe Model:** Unlike client-server models where clients talk directly to a server, MQTT decouples the sender (Publisher) from the receiver (Subscriber).
*   **Broker:** A central server (the MQTT Broker) acts as a post office. Publishers send messages to the broker, and Subscribers receive messages from the broker. Publishers and Subscribers generally don't know about each other directly.
*   **Topics:** Messages are published to specific "topics" (e.g., `sensors/power/dummy`, `home/livingroom/temperature`). Topics are like addresses or channels. They are hierarchical strings separated by forward slashes (`/`).
*   **Publish:** A device (like our ESP8266) *publishes* a message (the JSON payload) to a specific topic on the broker.
*   **Subscribe:** Another client (e.g., a data logging service, a dashboard application) *subscribes* to one or more topics on the broker.
*   **Message Delivery:** When the broker receives a message published to a topic, it forwards that message to all clients currently subscribed to that topic.

This model allows for flexible communication: one publisher can send data to many subscribers, or many publishers can send data to one or more subscribers, all managed by the central broker based on topic subscriptions.
