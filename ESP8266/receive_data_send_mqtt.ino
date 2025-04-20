#include <ESP8266WiFi.h>
// #include <WiFiClientSecure.h> // Uncomment if using MQTTS (port 8883) and configure below.
#include <PubSubClient.h>
#include <ArduinoJson.h>      // Using ArduinoJson v6 or later
#include <WiFiUdp.h>          // Required for NTPClient
#include <NTPClient.h>        // For getting network time

// --- Credentials as Macros ---
// Replace placeholders with your actual network and broker details.
// These can be overridden by build flags if using PlatformIO.
#ifndef WIFI_SSID
#define WIFI_SSID "<YOUR_WIFI_SSID>" // Your WiFi network name
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "<YOUR_WIFI_PASSWORD>" // Your WiFi password
#endif
#ifndef MQTT_SERVER
#define MQTT_SERVER "<YOUR_MQTT_BROKER_IP>" // IP address or hostname of your MQTT broker
#endif
#ifndef MQTT_USER
#define MQTT_USER "<YOUR_MQTT_USER>" // MQTT username (leave blank "" if none)
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD "<YOUR_MQTT_PASSWORD>" // MQTT password (leave blank "" if none)
#endif

// --- Configuration Constants ---
const int MQTT_PORT = 1883; // Default MQTT port (use 8883 for MQTTS/TLS)
// Client ID must be unique for each device connecting to the same MQTT broker.
const char* MQTT_CLIENT_ID = "esp8266-serial-receiver-01"; // Example unique ID
// Topic where the ESP8266 will publish the power data.
const char* MQTT_TOPIC = "sensors/power/serial"; // Example topic

// MQTT Root CA Certificate (Required ONLY for MQTTS with server verification)
// const char* MQTT_ROOT_CA = NULL; // Example: Set to your broker's Root CA certificate string if needed.
// Example format:
// const char* MQTT_ROOT_CA = \
// "-----BEGIN CERTIFICATE-----\n" \
// "MIID... (certificate content) ...=\n" \
// "-----END CERTIFICATE-----\n";

// --- Serial Configuration ---
// Baud rate for serial communication with the sending device (e.g., Arduino).
// IMPORTANT: This MUST match the baud rate set on the sending device.
const long SERIAL_BAUD_RATE = 115200; // Common baud rate, adjust if needed (e.g., 9600)

// --- Data Structures ---
// Structure to hold the parsed sensor data received via serial.
typedef struct {
    String device_id_from_serial; // Stores the device ID received via serial.
    float power;                  // Stores the power value received via serial.
    bool data_valid;              // Flag indicating if the last serial read was successfully parsed.
} SensorReading;

// Structure to hold a failed MQTT message for retry attempts.
struct FailedMessage {
    char payload[256]; // Buffer for the JSON payload. Adjust size if your JSON is larger.
};

// --- Global Variables ---
// Sensor Data
SensorReading latestReading;   // Holds the most recently parsed reading.
bool newDataAvailable = false; // Flag set to true when new valid serial data is parsed and ready to send.

// MQTT Retry Logic
FailedMessage pendingRetryMessage; // Stores the payload of the last failed message.
bool retryPending = false;         // Flag indicating if a message is waiting to be retried.
unsigned long lastRetryAttemptTime = 0; // Timestamp of the last retry attempt.
const int MAX_RETRY_DELAY_MS = 60000;   // Maximum delay between retries (e.g., 60 seconds).
const int INITIAL_RETRY_DELAY_MS = 5000; // Initial delay before the first retry (e.g., 5 seconds).
int currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Current delay, increases exponentially on failure.

// WiFi and MQTT Clients
WiFiClient wifiClient; // Use standard WiFiClient for non-secure MQTT (port 1883).
// WiFiClientSecure wifiClient; // Use WiFiClientSecure for MQTTS (port 8883). Remember to uncomment includes and config.
PubSubClient client(wifiClient); // MQTT client instance.

// NTP Client for Time Synchronization
const char* NTP_SERVER = "pool.ntp.org"; // Standard NTP server pool.
const long UTC_OFFSET_SECONDS = 19800;   // Timezone offset from UTC in seconds (e.g., IST = +5:30 = 19800).
WiFiUDP ntpUDP;                          // UDP client for NTP communication.
// NTPClient constructor: UDP client, NTP server, UTC offset, Update interval (handled manually in loop).
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET_SECONDS, 60 * 60 * 1000);

// Timing Variables
unsigned long lastNtpUpdateTime = 0;     // Timestamp of the last successful NTP update attempt.
const long NTP_UPDATE_INTERVAL_MS = 60000; // How often to attempt NTP sync (e.g., 60 seconds).

// --- Function Prototypes ---
void setupWiFi();
void connectMQTT();
bool publishData(const char* payload);
void readAndProcessSerialData();
void handleMQTT();
void setupMQTTClient();
String getNTPTimestamp();

// --- Setup Function ---
// Runs once when the ESP8266 boots up.
void setup() {
    // Initialize Serial for debugging output (TX pin = GPIO1).
    Serial.begin(115200);
    delay(100); // Short delay for serial initialization.
    Serial.println("\nStarting ESP8266 Serial Power Monitor...");

    // Initialize Serial for receiving data from the sensor device (RX pin = GPIO3).
    // Note: ESP8266 has only one hardware Serial (Serial). If debugging and sensor
    // communication use different baud rates, you might need SoftwareSerial or
    // careful management. Here, we assume the debug rate (115200) might differ
    // from the required sensor rate (SERIAL_BAUD_RATE).
    if (SERIAL_BAUD_RATE != 115200) {
        Serial.println("Warning: Debug Serial (115200) and Sensor Serial (" + String(SERIAL_BAUD_RATE) + ") differ.");
        // If they MUST be different and use the hardware Serial port, re-initialize after debug prints:
        // Serial.end(); // Close the debug serial connection.
        // Serial.begin(SERIAL_BAUD_RATE); // Re-open with the sensor baud rate.
        // Serial.println("Serial port re-initialized for sensor data at " + String(SERIAL_BAUD_RATE) + " baud.");
    } else {
        Serial.println("Using Serial port for sensor data at " + String(SERIAL_BAUD_RATE) + " baud.");
    }
    Serial.println("Waiting for data in format: (device_id, power_value)");

    // Establish WiFi connection.
    setupWiFi();

    // Initialize the NTP client after WiFi is connected.
    Serial.println("Initializing NTP client...");
    timeClient.begin();

    // Configure the MQTT client (server address, port, etc.).
    setupMQTTClient();

    Serial.println("Setup complete. Entering main loop.");
    lastNtpUpdateTime = millis(); // Initialize the NTP update timer.
}

// --- Main Loop Function ---
// Runs repeatedly after setup() completes.
void loop() {
    // 1. Check for and process any incoming data on the serial port.
    readAndProcessSerialData();

    // 2. Handle MQTT connection, message publishing, and retry logic.
    handleMQTT(); // This also calls client.loop() internally.

    // 3. Periodically attempt to update the time via NTP.
    if (millis() - lastNtpUpdateTime >= NTP_UPDATE_INTERVAL_MS) {
        Serial.println("Attempting NTP time update...");
        bool updateSuccess = timeClient.update(); // Non-blocking update attempt.
        if (updateSuccess) {
            Serial.println("NTP time update successful.");
        } else {
            Serial.println("NTP time update failed (will retry later).");
        }
        lastNtpUpdateTime = millis(); // Reset the timer regardless of success.
    }

    // 4. Yield CPU time to allow background tasks (like WiFi handling) to run.
    yield();
}

// --- WiFi Setup Function ---
// Connects the ESP8266 to the configured WiFi network.
void setupWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA); // Set ESP8266 to Station mode (connect to an existing AP).
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    // Wait for connection, with a timeout.
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected successfully.");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi connection FAILED after multiple attempts. Check credentials/signal. Restarting ESP...");
        delay(5000); // Wait a bit before restarting.
        ESP.restart(); // Restart the ESP8266 to try again.
    }
}

// --- Configure MQTT Client Function ---
// Sets up the MQTT client parameters (server, port, buffer size, TLS/SSL if needed).
void setupMQTTClient() {
    // --- MQTTS (TLS/SSL) Configuration - Uncomment and adapt if needed ---
    // Requires <WiFiClientSecure.h> include and using WiFiClientSecure object.
    /*
    #ifdef MQTT_ROOT_CA
        // Option 1: Verify server certificate using Root CA (Recommended for production)
        // Requires BearSSL library on ESP8266.
        BearSSL::X509List caList(MQTT_ROOT_CA);
        wifiClient.setTrustAnchors(&caList);
        Serial.println("Configured WiFiClientSecure with Root CA for server verification.");

        // Option 2: Skip server certificate verification (Less secure, useful for testing)
        // wifiClient.setInsecure();
        // Serial.println("WARNING: Skipping MQTT server certificate verification (setInsecure)!");
    #else
        // If MQTTS port (e.g., 8883) is used but no CA is defined, default to insecure.
        // wifiClient.setInsecure();
        // Serial.println("WARNING: MQTTS port used, but no Root CA defined. Skipping server certificate verification!");
    #endif
    */
    // --- End MQTTS Configuration ---

    // Set the MQTT broker server address and port.
    client.setServer(MQTT_SERVER, MQTT_PORT);
    // Set the buffer size for MQTT messages. Ensure it's large enough for your JSON payload + overhead.
    client.setBufferSize(512);
    // Set the callback function for handling incoming MQTT messages (if subscribing).
    // client.setCallback(mqttCallback); // Uncomment and implement mqttCallback if needed.
}


// --- MQTT Connection Function ---
// Establishes or re-establishes connection to the MQTT broker. Blocking operation.
void connectMQTT() {
    // Loop until connected.
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        bool connectResult;

        // Attempt connection with or without credentials based on configuration.
        if (strlen(MQTT_USER) > 0) {
            Serial.print(" (User: "); Serial.print(MQTT_USER); Serial.print(")...");
            connectResult = client.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD);
        } else {
            Serial.print(" (No Auth)...");
            connectResult = client.connect(MQTT_CLIENT_ID);
        }

        if (connectResult) {
            Serial.println(" connected.");
            // Reset retry logic upon successful connection.
            currentRetryDelay = INITIAL_RETRY_DELAY_MS;
            retryPending = false;
            // --- Subscribe to topics here if needed ---
            // Example: client.subscribe("cmnd/device/power");
            // -----------------------------------------
        } else {
            // Print detailed error information if connection failed.
            Serial.print(" failed, rc=");
            Serial.print(client.state()); // Print the Paho client state code.
            Serial.print(" | WiFi: ");
            Serial.print(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
            Serial.print(" | Server: "); Serial.print(MQTT_SERVER); Serial.print(":"); Serial.println(MQTT_PORT);
            // Add specific SSL/TLS error checks here if using WiFiClientSecure.
            // Example: Serial.println(wifiClient.getLastSSLError());
            Serial.println(" Retrying in 5 seconds...");
            // Wait before retrying connection. Yield during wait.
            long startWait = millis();
            while (millis() - startWait < 5000) {
                yield();
            }
        }
    }
}

// --- Handle MQTT Loop, Publishing, and Retries ---
// Should be called repeatedly in the main loop.
void handleMQTT() {
    // Don't attempt MQTT operations if WiFi is disconnected.
    if (WiFi.status() != WL_CONNECTED) {
        // Avoid flooding serial monitor if WiFi is down.
        // Serial.println("WiFi disconnected. Cannot handle MQTT.");
        return;
    }

    // If not connected to MQTT, attempt to reconnect.
    if (!client.connected()) {
        connectMQTT(); // This is a blocking call.
    }

    // Process MQTT messages (keep-alive, incoming messages, etc.). Essential!
    client.loop();

    // --- Publishing Logic ---
    // Check if new, valid data is available and MQTT is connected.
    if (newDataAvailable && latestReading.data_valid && client.connected()) {

        // Prepare JSON payload using ArduinoJson.
        StaticJsonDocument<256> jsonDoc; // Adjust size if needed based on your JSON structure.

        jsonDoc["reporterDeviceId"] = MQTT_CLIENT_ID; // ID of this ESP8266 device.
        jsonDoc["sourceDeviceId"] = latestReading.device_id_from_serial; // ID received from serial.
        jsonDoc["timestamp"] = getNTPTimestamp(); // Get current timestamp.
        jsonDoc["power"] = latestReading.power;   // The power value.
        // Add other fields if needed, e.g., signal strength:
        // jsonDoc["rssi"] = WiFi.RSSI();

        // Serialize JSON document to a character buffer.
        char jsonBuffer[256]; // Ensure buffer size matches StaticJsonDocument size.
        size_t jsonSize = serializeJson(jsonDoc, jsonBuffer);

        // Check if serialization was successful and buffer was large enough.
        if (jsonSize > 0 && jsonSize < sizeof(jsonBuffer)) {
            Serial.printf("Publishing JSON (%d bytes): %s\n", jsonSize, jsonBuffer);
            // Attempt to publish the JSON payload.
            if (!publishData(jsonBuffer)) {
                // Publish failed. publishData() handles queuing for retry.
                Serial.println("Publish attempt failed, queued for retry.");
            }
        } else {
            Serial.println("JSON serialization failed or buffer too small!");
        }

        // Reset flags after attempting to publish (or queueing).
        newDataAvailable = false;
        latestReading.data_valid = false; // Data is considered processed.
    }

    // --- Retry Logic ---
    // Check if a message is pending retry and MQTT is connected.
    if (retryPending && client.connected()) {
        // Check if the current retry delay has elapsed.
        if (millis() - lastRetryAttemptTime >= currentRetryDelay) {
            Serial.print("Retrying queued message... ");
            // Attempt to publish the stored message again.
            if (publishData(pendingRetryMessage.payload)) {
                Serial.println("Retry successful.");
                retryPending = false; // Clear the retry flag.
                currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Reset delay for next potential failure.
            } else {
                Serial.println("Retry FAILED.");
                lastRetryAttemptTime = millis(); // Update last attempt time.
                // Increase the delay exponentially, up to the maximum limit.
                currentRetryDelay = min(currentRetryDelay * 2, MAX_RETRY_DELAY_MS);
                Serial.print("Increased retry delay to ");
                Serial.print(currentRetryDelay);
                Serial.println(" ms");
            }
        }
    }
}

// --- Publish Data Function with Retry Handling ---
// Attempts to publish the payload. Returns true on success, false on failure.
// Handles queuing the message for retry on failure if no other retry is pending.
bool publishData(const char* payload) {
    // Check MQTT connection status before attempting to publish.
    if (!client.connected()) {
        Serial.println("MQTT not connected. Cannot publish.");
        // Do not queue for retry if not connected; wait for reconnect.
        return false;
    }

    // Attempt to publish the message to the configured topic.
    if (client.publish(MQTT_TOPIC, payload)) {
        // Publish successful.
        // Serial.println("Publish successful."); // Keep log less verbose.
        return true;
    } else {
        // Publish failed.
        Serial.println("Publish FAILED.");
        // Store the message for retry ONLY if no other message is already pending.
        if (!retryPending) {
            // Copy the payload into the retry buffer, ensuring null termination.
            strncpy(pendingRetryMessage.payload, payload, sizeof(pendingRetryMessage.payload) - 1);
            pendingRetryMessage.payload[sizeof(pendingRetryMessage.payload) - 1] = '\0';
            retryPending = true; // Set the retry flag.
            lastRetryAttemptTime = millis(); // Record the time of failure.
            currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Reset to initial delay.
            Serial.println("Stored failed message for retry.");
        } else {
            // If another retry is already pending, discard this new failed message.
            Serial.println("Another retry is already pending. Discarding new failed message.");
        }
        return false; // Indicate publish failure.
    }
}

// --- Read and Process Serial Data Function ---
// Checks for incoming serial data, parses it, and updates the global reading struct.
void readAndProcessSerialData() {
    // Check if any data is available on the Serial port.
    if (Serial.available() > 0) {
        // Read the incoming data until a newline character is received.
        String inputString = Serial.readStringUntil('\n');
        inputString.trim(); // Remove leading/trailing whitespace and carriage returns.

        // Only process non-empty strings.
        if (inputString.length() > 0) {
            Serial.print("Received Serial: ");
            Serial.println(inputString);

            // Check if the string matches the expected format: "(device_id, power_value)".
            if (inputString.startsWith("(") && inputString.endsWith(")")) {
                // Remove the parentheses.
                inputString = inputString.substring(1, inputString.length() - 1);

                // Find the comma separator.
                int commaIndex = inputString.indexOf(',');

                if (commaIndex != -1) {
                    // Extract the parts before and after the comma.
                    String deviceIdStr = inputString.substring(0, commaIndex);
                    String powerStr = inputString.substring(commaIndex + 1);

                    // Trim whitespace from the extracted parts.
                    deviceIdStr.trim();
                    powerStr.trim();

                    // Convert the power string to a floating-point number.
                    float powerValue = powerStr.toFloat();

                    // Basic validation: Check if device ID is not empty and power conversion was likely successful.
                    // Note: toFloat() returns 0.0 on failure. We check if the string was actually "0" or "0.0"
                    // to distinguish a valid zero reading from a conversion error.
                    bool conversionOk = (powerValue != 0.0) || (powerStr == "0") || (powerStr == "0.0");

                    if (!deviceIdStr.isEmpty() && conversionOk) {
                        // Update the global reading structure with the parsed data.
                        latestReading.device_id_from_serial = deviceIdStr;
                        latestReading.power = powerValue;
                        latestReading.data_valid = true; // Mark data as valid.
                        newDataAvailable = true;         // Signal that new data is ready to be published.

                        Serial.print("Parsed OK -> Device: '");
                        Serial.print(latestReading.device_id_from_serial);
                        Serial.print("', Power: ");
                        Serial.println(latestReading.power);

                    } else {
                        // Parsing failed due to invalid format after the comma.
                        Serial.println("Parsing Error: Invalid device ID or power value format after comma.");
                        latestReading.data_valid = false;
                    }
                } else {
                    // Parsing failed because the comma separator was not found.
                    Serial.println("Parsing Error: Comma separator not found.");
                    latestReading.data_valid = false;
                }
            } else {
                // Parsing failed because the string didn't start/end with parentheses.
                Serial.println("Parsing Error: Input string does not match expected format '(device_id, power_value)'.");
                latestReading.data_valid = false;
            }
        } // End if inputString.length() > 0
    } // End if Serial.available() > 0
}

// --- Get NTP Timestamp Function ---
// Retrieves the current time from the NTP client and formats it.
// Returns millis() as a fallback if NTP time is not yet synchronized.
String getNTPTimestamp() {
    // Get the Unix epoch time (seconds since 1970-01-01 UTC).
    unsigned long epochTime = timeClient.getEpochTime();

    // Check if the time seems valid (e.g., after a known date like Jan 1, 2023).
    // 1672531200 is the Unix timestamp for 2023-01-01 00:00:00 GMT.
    // Also check if the timeClient library considers the time to be set.
    if (timeClient.isTimeSet() && epochTime > 1672531200) {
        // Return the time formatted as an ISO 8601 string (e.g., "2023-10-27T10:30:00Z").
        // Note: getFormattedTime() in NTPClient library typically returns this format.
        return timeClient.getFormattedTime();
    } else {
        // Fallback if NTP time isn't available or seems invalid.
        Serial.println("NTP time not available/valid, using millis() as fallback timestamp.");
        // Return milliseconds since boot as a String.
        return String(millis());
    }
}
