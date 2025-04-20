// dummy_data_send_mqtt.ino
// ESP8266 code to generate dummy power data internally for all devices
// in a batch and send via MQTT at a configured interval.

#include <ESP8266WiFi.h>
// #include <WiFiClientSecure.h> // For MQTTS - Uncomment if using MQTTS
#include <PubSubClient.h>
#include <ArduinoJson.h>      // Using ArduinoJson v6 or later
#include <WiFiUdp.h>          // Added for NTP
#include <NTPClient.h>        // Added for NTP

// --- Configuration Macros ---
// WiFi Credentials (Provide defaults, can be overridden by build flags)
#ifndef WIFI_SSID
#define WIFI_SSID "<YOUR_WIFI_SSID>" // Replace with your WiFi SSID
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "<YOUR_WIFI_PASSWORD>" // Replace with your WiFi password
#endif

// MQTT Broker Details (Provide defaults, can be overridden by build flags)
#ifndef MQTT_SERVER
#define MQTT_SERVER "<YOUR_MQTT_BROKER_IP>" // Replace with your MQTT broker IP or hostname
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883 // Default MQTT port (use 8883 for MQTTS)
#endif
#ifndef MQTT_USER
#define MQTT_USER "<YOUR_MQTT_USER>" // If required, leave empty "" if not
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD "<YOUR_MQTT_PASSWORD>" // If required, leave empty "" if not
#endif
// Use a unique client ID for each device connected to the broker
#ifndef MQTT_CLIENT_ID
#define MQTT_CLIENT_ID "esp8266-dummy-batch-sender"
#endif
#ifndef MQTT_TOPIC
#define MQTT_TOPIC "sensors/power/dummy" // Topic for dummy data
#endif

// MQTT Root CA Certificate (Required for MQTTS server verification)
// #define MQTT_ROOT_CA NULL // Set if using MQTTS with verification

// --- Dummy Data Configuration ---
#define DUMMY_DATA_INTERVAL_MS (60 * 1000) // Interval between sending batches (60 seconds)
#define DELAY_BETWEEN_MESSAGES_MS 50       // Small delay between messages within a batch (ms)

// Define device IDs for the simulated loads
const char* dummyDeviceIds[] = {"DummyLoad_A", "DummyLoad_B", "DummyLoad_C"};
const int NUM_DUMMY_DEVICES = sizeof(dummyDeviceIds) / sizeof(dummyDeviceIds[0]);

// --- NTP Configuration ---
#define NTP_SERVER "pool.ntp.org"
#define UTC_OFFSET_SECONDS 19800 // IST: UTC+5:30 = 5.5 * 3600
#define NTP_UPDATE_INTERVAL_MS (60 * 1000) // Update NTP every 60 seconds (60000 ms)

// --- MQTT Retry Configuration ---
#define MAX_RETRY_DELAY_MS 60000
#define INITIAL_RETRY_DELAY_MS 5000

// MQTT Retry Logic Globals
struct FailedMessage {
    char payload[256]; // Adjust size based on expected JSON payload
};
FailedMessage pendingRetryMessage;
bool retryPending = false;
unsigned long lastRetryAttemptTime = 0;
int currentRetryDelay = INITIAL_RETRY_DELAY_MS;

// WiFi and MQTT Clients
WiFiClient wifiClient; // Use WiFiClient for non-secure MQTT (port 1883)
// WiFiClientSecure wifiClient; // Use for MQTTS (port 8883)
PubSubClient client(wifiClient);

// NTP Client
WiFiUDP ntpUDP;
// Note: Last arg (update interval) is handled differently by NTPClient library, loop logic uses NTP_UPDATE_INTERVAL_MS
NTPClient timeClient(ntpUDP, NTP_SERVER, UTC_OFFSET_SECONDS, 60 * 60 * 1000);

// Timing variables
unsigned long lastDummyDataSendTime = 0; // Timer for sending dummy data batch
unsigned long lastNtpUpdateTime = 0;

// --- Function Prototypes ---
void setupWiFi();
void connectMQTT();
bool publishData(const char* payload);
void generateAndPublishDummyDataBatch();
void handleMQTT();
void setupMQTTClient();
String getNTPTimestamp();

// --- Setup ---
void setup() {
    // Initialize Serial for debugging output
    Serial.begin(115200);
    delay(100);
    Serial.println("\nStarting ESP8266 Dummy Power Monitor (Batch Mode)...");

    // Initialize random seed
    randomSeed(micros());

    setupWiFi(); // Connect to WiFi first

    Serial.println("Initializing NTP client...");
    timeClient.begin();

    setupMQTTClient();

    Serial.println("Setup complete. Entering loop.");
    Serial.print("Will send dummy data batch every ");
    Serial.print(DUMMY_DATA_INTERVAL_MS / 1000);
    Serial.println(" seconds.");

    lastNtpUpdateTime = millis(); // Initialize NTP timing
    // Initialize dummy data timer slightly offset so first send isn't immediate (optional)
    lastDummyDataSendTime = millis() - DUMMY_DATA_INTERVAL_MS + 5000; // Start first send after ~5 sec
}

// --- Main Loop ---
void loop() {
    // 1. Maintain MQTT Connection and process messages/publishing/retries
    handleMQTT(); // Handles connection, retry logic, and client.loop()

    // 2. Check if it's time to generate and send a batch of dummy data
    if (millis() - lastDummyDataSendTime >= DUMMY_DATA_INTERVAL_MS) {
        generateAndPublishDummyDataBatch(); // Call the batch function
        lastDummyDataSendTime = millis(); // Reset the timer for the next batch
    }

    // 3. Update NTP Time periodically (non-blocking)
    if (millis() - lastNtpUpdateTime >= NTP_UPDATE_INTERVAL_MS) {
        Serial.println("Attempting NTP time update...");
        bool updateSuccess = timeClient.update();
        if (updateSuccess) {
            Serial.println("NTP time update successful.");
        } else {
            Serial.println("NTP time update failed (will retry later).");
        }
        lastNtpUpdateTime = millis();
    }

    // 4. Yield to allow background processes
    yield();
}

// --- WiFi Setup ---
void setupWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi connection FAILED. Check credentials/signal. Restarting...");
        delay(5000);
        ESP.restart();
    }
}

// --- Configure MQTT Client ---
void setupMQTTClient() {
    // Configure WiFiClientSecure if using MQTTS
#ifdef MQTT_ROOT_CA
    // if (MQTT_ROOT_CA != NULL && strlen(MQTT_ROOT_CA) > 0) { // Macros are text replacement, check differently or assume defined means use
    // // For ESP8266 BearSSL:
    // BearSSL::X509List caList(MQTT_ROOT_CA);
    // wifiClient.setTrustAnchors(&caList);
    // Serial.println("Configured WiFiClientSecure with Root CA.");
    // } else {
    // Serial.println("WARNING: Skipping MQTT server certificate verification (setInsecure)!");
    // wifiClient.setInsecure(); // Use with caution!
    // }
#endif // MQTT_ROOT_CA

    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setBufferSize(512); // Ensure buffer is large enough
    // client.setCallback(callback); // Add if subscribing
}

// --- MQTT Connection ---
void connectMQTT() {
    // Loop until we're reconnected - consider a non-blocking approach for robust applications
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        bool connectResult;
        // Check if MQTT_USER macro is defined and not empty
        if (strlen(MQTT_USER) > 0) {
            connectResult = client.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD);
        } else {
            connectResult = client.connect(MQTT_CLIENT_ID);
        }

        if (connectResult) {
            Serial.println("connected");
            currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Reset retry delay on successful connect
            retryPending = false; // Clear any pending retry on successful connect
            // Subscribe here if needed
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.print(" | WiFi: ");
            Serial.print(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
            Serial.print(" | Server: ");
            Serial.print(MQTT_SERVER);
            Serial.print(":");
            Serial.println(MQTT_PORT);
            // Add SSL error check if using WiFiClientSecure
            Serial.println(" Retrying in 5 seconds...");
            long startWait = millis();
            while (millis() - startWait < 5000) {
                yield(); // Yield during wait
            }
        }
    }
}

// --- Handle MQTT Connection, Retries, and Client Loop ---
void handleMQTT() {
    if (WiFi.status() != WL_CONNECTED) {
        // Don't print constantly if WiFi is down
        return;
    }

    if (!client.connected()) {
        connectMQTT(); // Blocking attempt to reconnect
    }

    client.loop(); // Essential for MQTT keep-alive and incoming messages

    // --- Retry Logic ---
    // Note: Publishing logic is now called directly from the timer in loop()
    if (retryPending && client.connected()) {
        if (millis() - lastRetryAttemptTime >= currentRetryDelay) {
            Serial.print("Retrying queued message... ");
            if (publishData(pendingRetryMessage.payload)) {
                Serial.println("Retry successful.");
                retryPending = false;
                currentRetryDelay = INITIAL_RETRY_DELAY_MS;
            } else {
                Serial.println("Retry FAILED.");
                lastRetryAttemptTime = millis();
                // Exponential backoff for retry delay
                currentRetryDelay = min(currentRetryDelay * 2, (int)MAX_RETRY_DELAY_MS); // Cast macro
                Serial.print("Increased retry delay to ");
                Serial.print(currentRetryDelay);
                Serial.println(" ms");
            }
        }
    }
}

// --- Publish Data with Basic Retry ---
bool publishData(const char* payload) {
    if (!client.connected()) {
        Serial.println("MQTT not connected. Cannot publish.");
        // Don't queue for retry if not connected, wait for reconnect
        return false;
    }

    if (client.publish(MQTT_TOPIC, payload)) {
        // Serial.println("Publish successful."); // Keep log less verbose
        return true;
    } else {
        Serial.println("Publish FAILED.");
        // Store for retry ONLY if no other retry is pending
        if (!retryPending) {
            strncpy(pendingRetryMessage.payload, payload, sizeof(pendingRetryMessage.payload) - 1);
            pendingRetryMessage.payload[sizeof(pendingRetryMessage.payload) - 1] = '\0'; // Ensure null termination
            retryPending = true;
            lastRetryAttemptTime = millis(); // Record time of failure
            currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Start with initial delay
            Serial.println("Stored failed message for retry.");
        } else {
            Serial.println("Another retry is already pending. Discarding new failed message.");
        }
        return false;
    }
}

// --- Generate and Publish Dummy Sensor Data Batch ---
void generateAndPublishDummyDataBatch() {
    if (!client.connected()) {
        Serial.println("MQTT not connected. Skipping dummy data batch generation.");
        return;
    }

    Serial.println("--- Generating and sending dummy data batch ---");

    // Loop through all defined dummy devices
    for (int i = 0; i < NUM_DUMMY_DEVICES; i++) {
        const char* currentDeviceId = dummyDeviceIds[i];

        // Generate a dummy power value (adjust range as needed)
        float dummyPower = 50.0 + (random(0, 1500 + (i * 500)) / 10.0); // Example range

        Serial.print("  Device: ");
        Serial.print(currentDeviceId);
        Serial.print(", Power: ");
        Serial.println(dummyPower);

        // Prepare JSON payload for this device
        StaticJsonDocument<256> jsonDoc; // Adjust size if needed

        jsonDoc["reporterDeviceId"] = MQTT_CLIENT_ID; // Use macro for this ESP's ID
        jsonDoc["sourceDeviceId"] = currentDeviceId;  // The simulated device ID
        jsonDoc["timestamp"] = getNTPTimestamp();     // Get fresh timestamp for each message
        jsonDoc["power"] = dummyPower;
        // Add other fields if needed
        // jsonDoc["rssi"] = WiFi.RSSI();

        char jsonBuffer[256];
        size_t jsonSize = serializeJson(jsonDoc, jsonBuffer);

        if (jsonSize > 0 && jsonSize < sizeof(jsonBuffer)) {
            Serial.printf("  Publishing JSON (%d bytes): %s\n", jsonSize, jsonBuffer);
            // Attempt to publish
            if (!publishData(jsonBuffer)) {
                // Publish failed, message is queued for retry by publishData
                // Note: Current retry logic only handles the *first* failure in a batch.
            }
        } else {
            Serial.println("  JSON serialization failed or buffer too small!");
        }

        // Small delay between messages in the batch
        delay(DELAY_BETWEEN_MESSAGES_MS);
        yield(); // Allow background tasks

    } // End of loop through devices

    Serial.println("--- Finished sending dummy data batch ---");
}

// --- Get NTP Timestamp ---
String getNTPTimestamp() {
    unsigned long epochTime = timeClient.getEpochTime();
    // Check if epoch time seems valid (e.g., after Jan 1 2023)
    // 1672531200 = Unix timestamp for 2023-01-01 00:00:00 GMT
    if (timeClient.isTimeSet() && epochTime > 1672531200) {
        // Return time formatted as ISO 8601 (YYYY-MM-DDTHH:mm:ssZ)
        time_t rawTime = epochTime;
        struct tm* ti;
        ti = gmtime(&rawTime); // Get UTC time structure

        char isoBuffer[25]; // Buffer for ISO 8601 format
        // Format: YYYY-MM-DDTHH:MM:SSZ (Z indicates UTC)
        strftime(isoBuffer, sizeof(isoBuffer), "%Y-%m-%dT%H:%M:%SZ", ti);
        return String(isoBuffer);

        // Alternative: Use library's default format if preferred
        // return timeClient.getFormattedTime();
    } else {
        // Fallback if NTP time isn't available yet or is invalid
        Serial.println("NTP time not available/valid, using millis() as fallback timestamp.");
        return String(millis()); // Return milliseconds since boot as a String
    }
}
