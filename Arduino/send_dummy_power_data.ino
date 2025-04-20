// Arduino UNO code to send dummy power data for 3 devices over Serial

// --- Configuration ---
const long SERIAL_BAUD_RATE = 115200; // Must match the receiver (ESP8266)

// Define device IDs for the simulated loads
const char* deviceId1 = "Load_A";
const char* deviceId2 = "Load_B";
const char* deviceId3 = "Load_C";

// Timing interval for sending data (in milliseconds)
const unsigned long SEND_INTERVAL = 5000; // Send data every 5 seconds
unsigned long lastSendTime = 0;

// --- Setup ---
void setup() {
  // Initialize Serial communication
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.println("Arduino UNO Power Data Sender Initialized.");
  Serial.print("Sending data every ");
  Serial.print(SEND_INTERVAL / 1000);
  Serial.println(" seconds.");

  // Initialize random seed (optional but good for varied dummy data)
  randomSeed(analogRead(A0));

  lastSendTime = millis(); // Initialize timer
}

// --- Main Loop ---
void loop() {
  // Check if it's time to send the next batch of data
  if (millis() - lastSendTime >= SEND_INTERVAL) {

    // --- Simulate and Send Data for Device 1 ---
    float power1 = 100.0 + (random(0, 1000) / 10.0); // Simulate power between 100.0 and 199.9 W
    Serial.print("(");
    Serial.print(deviceId1);
    Serial.print(", ");
    Serial.print(power1, 1); // Send power with 1 decimal place
    Serial.println(")"); // Use println to add the newline character

    // Short delay between messages to allow receiver processing time (optional)
    delay(50);

    // --- Simulate and Send Data for Device 2 ---
    float power2 = 50.0 + (random(0, 500) / 10.0); // Simulate power between 50.0 and 99.9 W
    Serial.print("(");
    Serial.print(deviceId2);
    Serial.print(", ");
    Serial.print(power2, 1);
    Serial.println(")");

    delay(50);

    // --- Simulate and Send Data for Device 3 ---
    float power3 = 200.0 + (random(0, 2000) / 10.0); // Simulate power between 200.0 and 399.9 W
    Serial.print("(");
    Serial.print(deviceId3);
    Serial.print(", ");
    Serial.print(power3, 1);
    Serial.println(")");

    Serial.println("--- Sent data batch ---"); // Debug message on Arduino's Serial Monitor

    lastSendTime = millis(); // Update the last send time
  }

  // You can add other Arduino tasks here if needed,
  // but keep the loop running smoothly.
}
