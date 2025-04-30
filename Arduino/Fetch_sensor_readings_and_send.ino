#include "ACS712.h" //5AMPA
#include <Wire.h> 
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27,16,2); 
double sensorValue1 = 0;
double sensorValue2 = 0;
int crosscount = 0;
int climb_flag = 0;
int val[100];   // Array to store sensor values
int max_v = 0;
double VmaxD = 0;  // Max voltage
double VeffD = 0;  // Effective voltage
double Veff = 0;   // Resulting voltage
ACS712 sensor(ACS712_05B, A0);
ACS712 senso(ACS712_05B, A1);
ACS712 sens(ACS712_05B, A2);
float U = 230;
// Setup function: Initializes the program
void setup() {
  Serial.begin(115200);  // Initialize serial communication at 9600 baud
  lcd.init();
  lcd.backlight();
  lcd.setCursor(3,0);
  lcd.print(" Power");
  sensor.calibrate();
  senso.calibrate();
  sens.calibrate();
}

// Loop function: Main program logic runs repeatedly
void loop() {
  // Read and process sensor values
  for (int i = 0; i < 100; i++) {
    sensorValue1 = analogRead(A3);  // Read analog sensor value from A0
    if (analogRead(A3) > 511) {
      val[i] = sensorValue1;  // Store sensor value in the array if it's greater than 511
    } else {
      val[i] = 0;  // Otherwise, set the value to 0
    }
    delay(1);  // Short delay for stability
  }

  // Find the maximum sensor value in the array
  max_v = 0;
  for (int i = 0; i < 100; i++) {
    if (val[i] > max_v) {
      max_v = val[i];  // Update max_v if a higher value is found
    }
    val[i] = 0;  // Reset the array element to 0
  }

  // Calculate effective voltage based on the maximum sensor value
  if (max_v != 0) {
    VmaxD = max_v;  // Set VmaxD to the maximum sensor value
    VeffD = VmaxD / sqrt(2);  // Calculate effective voltage (RMS) from VmaxD
    Veff = (((VeffD - 420.76) / -90.24) * -210.2) + 210.2;  // Apply calibration and scaling to Veff
  } else {
    Veff = 0;  // If no maximum value, set Veff to 0
  }

  // Print the calculated voltage to the serial monitor
  float I = sensor.getCurrentAC();
  float J = senso.getCurrentAC();
  float K = sens.getCurrentAC();
  if(I<0.09)
  {
    I=0;
  }
   if(J<0.09)
  {
    J=0;
  }
   if(K<0.09)
  {
    K=0;
  }
  int P = U * I;
  int P1 = U * J;
  int P2 = U * K;
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("D1:");
  lcd.print(P,1);
  lcd.setCursor(8,0);
  lcd.print("D2:");
  lcd.print(P1,1);
  lcd.setCursor(0,1);
  lcd.print("D3:");
  lcd.print(P2,1);
  // Serial.print("Voltage: ");
  // Serial.println(Veff);
  Serial.println(String("(D1,") + P + ")");
  delay(2000);
  Serial.println(String("(D2,") + P1 + ")");
  delay(2000);
  Serial.println(String("(D3,") + P2 + ")");
  delay(2000);
  VmaxD = 0;  // Reset VmaxD for the next iteration

  delay(5000);  // Delay for 100 milliseconds before the next loop
}