# ESP8266 Serial Data to MQTT Bridge

This Arduino sketch runs on an ESP8266 microcontroller. Its primary function is to receive data packets over a serial connection, parse them, format them into JSON, and publish them to an MQTT broker. It includes error handling for MQTT publishing failures with a retry mechanism.

## Overview

The sketch performs the following tasks:

1.  **Connects to WiFi:** Uses predefined credentials to establish a connection to a local WiFi network.
2.  **Connects to MQTT Broker:** Establishes a connection to an MQTT broker using specified server details and credentials.
3.  **Listens for Serial Data:** Continuously monitors the hardware serial port (RX pin) for incoming data.
4.  **Parses Serial Data:** Expects data in the format `(device_id, power_value)` on a single line, terminated by a newline character (`\n`).
5.  **Gets Timestamp:** Retrieves the current time from an NTP server to include in the data packet.
6.  **Formats Data:** Creates a JSON payload containing the received `sourceDeviceId`, the `power` value, a `timestamp`, and the ESP8266's own `reporterDeviceId`.
7.  **Publishes to MQTT:** Sends the JSON payload to a predefined MQTT topic.
8.  **Handles Errors:** If publishing fails (e.g., due to temporary network issues), it stores the message and attempts to resend it later with an exponential backoff delay.
9.  **Maintains Connections:** Automatically attempts to reconnect to WiFi and MQTT if the connection is lost.

## Hardware Setup

1.  **ESP8266 Board:** Any ESP8266-based board (like NodeMCU, Wemos D1 Mini).
2.  **Power Supply:** Provide appropriate power to the ESP8266 board (usually via USB or a 3.3V supply).
3.  **Serial Connection:**
    *   Connect the **TX (Transmit)** pin of the device *sending* the data (e.g., another Arduino, a sensor interface) to the **RX (Receive)** pin of the ESP8266 board (usually GPIO3).
    *   Connect the **GND (Ground)** of the sending device to the **GND** of the ESP8266 board. This is crucial for reliable serial communication.
    *   **Important:** Ensure the sending device uses the same `SERIAL_BAUD_RATE` (default 115200) as configured in this sketch.
4.  **WiFi Network:** An accessible 2.4GHz WiFi network is required for the ESP8266 to connect to the internet and the MQTT broker.
5.  **MQTT Broker:** An MQTT broker must be running and accessible from the ESP8266 over the network (e.g., Mosquitto, HiveMQ, AWS IoT Core).

## Data Flow

1.  **Reception:** The ESP8266 listens on its `Serial` RX pin. It expects data formatted as `(some_device_id,123.45)\n`.
2.  **Parsing:** When a newline character is detected, the received string is read. The sketch checks if it starts with `(` and ends with `)`. If so, it extracts the `device_id` string and the `power_value` string separated by a comma. The power value is converted to a floating-point number.
3.  **Timestamping:** The sketch fetches the current UTC time from an NTP server. If NTP is unavailable, it uses the milliseconds since the ESP8266 booted as a fallback timestamp.
4.  **JSON Creation:** A JSON object is constructed:
    ```json
    {
      "reporterDeviceId": "esp8266-serial-receiver", // ID of this ESP8266
      "sourceDeviceId": "some_device_id",         // ID received via serial
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ",        // NTP timestamp (UTC) or millis()
      "power": 123.45                             // Power value received via serial
    }
    ```
5.  **MQTT Transmission:** The JSON object is serialized into a string and published to the configured `mqtt_topic` (default: `sensors/power/serial`) on the connected MQTT broker.

## Error Handling (MQTT Publishing)

If the `client.publish()` command fails while the ESP8266 is connected to the broker (this might happen due to transient network issues or broker problems):

1.  **Failure Detection:** The sketch detects the `publish()` failure.
2.  **Store Message:** If no other message is already pending retry, the failed JSON payload is copied into a temporary buffer (`pendingRetryMessage`).
3.  **Set Retry Flag:** A flag (`retryPending`) is set to true.
4.  **Schedule Retry:** The initial retry delay (`INITIAL_RETRY_DELAY_MS`, default 5000ms) is set.
5.  **Retry Attempts:** In the main loop (`handleMQTT`), if the `retryPending` flag is true and the MQTT client is connected:
    *   It checks if the current retry delay has elapsed since the last attempt.
    *   If yes, it attempts to publish the stored message again.
    *   **Success:** If the retry succeeds, the `retryPending` flag is cleared, and the retry delay is reset to the initial value.
    *   **Failure:** If the retry fails again, the timestamp for the last attempt is updated, and the retry delay is doubled (exponential backoff), up to a maximum (`MAX_RETRY_DELAY_MS`, default 60000ms). This prevents overwhelming the network or broker during extended outages.
6.  **Discarding:** If a *new* message fails to publish while *another* message is already waiting for retry, the new message is discarded to prevent complex queue management. Only the first failed message is retried.

## Configuration

Before uploading the sketch, you **must** configure the following settings near the top of the `receive_data_send_mqtt.ino` file:

**Credentials (Macros):**

These are defined using `#define` and wrapped in `#ifndef` guards, allowing them to be potentially overridden by build flags (e.g., in PlatformIO's `platformio.ini`). If not overridden, the default values in the code are used.

*   `WIFI_SSID`: Your WiFi network name (SSID).
    ```cpp
    #define WIFI_SSID "YourWifiNetworkName"
    ```
*   `WIFI_PASSWORD`: Your WiFi password.
    ```cpp
    #define WIFI_PASSWORD "YourWifiPassword"
    ```
*   `MQTT_SERVER`: The IP address or hostname of your MQTT broker.
    ```cpp
    #define MQTT_SERVER "192.168.1.100" // Or "mqtt.example.com"
    ```
*   `MQTT_USER`: The username for MQTT authentication (leave empty `""` if none).
    ```cpp
    #define MQTT_USER "your_mqtt_username"
    ```
*   `MQTT_PASSWORD`: The password for MQTT authentication (leave empty `""` if none).
    ```cpp
    #define MQTT_PASSWORD "your_mqtt_password"
    ```

**Other Configuration (Constants):**

*   `mqtt_port`: The port number for the MQTT broker (default `1883` for unencrypted MQTT, use `8883` for MQTTS/TLS).
    ```cpp
    const int mqtt_port = 1883;
    ```
*   `mqtt_client_id`: A unique identifier for this ESP8266 client connecting to the broker. Must be unique among all clients connected to the same broker.
    ```cpp
    const char* mqtt_client_id = "esp8266-serial-receiver-01";
    ```
*   `mqtt_topic`: The MQTT topic where the JSON data will be published.
    ```cpp
    const char* mqtt_topic = "home/livingroom/power/serial";
    ```
*   `SERIAL_BAUD_RATE`: The baud rate for serial communication with the sending device. **Must match the sender's baud rate.**
    ```cpp
    const long SERIAL_BAUD_RATE = 115200; // Or 9600, etc.
    ```
*   `utcOffsetInSeconds`: Your local time zone offset from UTC in seconds (e.g., IST is UTC+5:30, so 5.5 * 3600 = 19800). Used for NTP.
    ```cpp
    const long utcOffsetInSeconds = 19800;
    ```

## Dependencies (Libraries)

This sketch requires the following Arduino libraries:

*   `ESP8266WiFi`: For WiFi connectivity (usually included with ESP8266 board support).
*   `PubSubClient`: For MQTT communication (install via Arduino Library Manager).
*   `ArduinoJson`: For creating and parsing JSON data (install v6.x or later via Arduino Library Manager).
*   `NTPClient`: For getting network time (install via Arduino Library Manager).
*   `WiFiUdp`: Required by NTPClient (usually included with ESP8266 board support).
*   *(Optional)* `WiFiClientSecure`: Needed if connecting to MQTT over TLS/SSL (MQTTS on port 8883). Uncomment related lines if used.

## How to Use

1.  Install the Arduino IDE or PlatformIO.
2.  Install the required libraries mentioned above.
3.  Install the ESP8266 board support package in your IDE.
4.  Open the `receive_data_send_mqtt.ino` file.
5.  Modify the **Configuration** section with your specific WiFi, MQTT, and other details.
6.  Connect the ESP8266 board to your computer via USB.
7.  Select the correct ESP8266 board type and COM port in your IDE.
8.  Compile and upload the sketch to the ESP8266.
9.  Connect the serial data source device to the ESP8266's RX and GND pins.
10. Power both devices.
11. Open the Serial Monitor in the Arduino IDE (set baud rate to 115200) to view debug messages and connection status.
12. Use an MQTT client (like MQTT Explorer, mosquitto_sub) to subscribe to the `mqtt_topic` you configured and observe the incoming JSON data.

