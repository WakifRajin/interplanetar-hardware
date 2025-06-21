
// this is a test file and hasnt been tested

#include <Wire.h>
#include <AS5600.h>

AS5600 encoder;

void setup() {
  Serial.begin(9600);
  Wire.begin();

  if (!encoder.begin()) {
    Serial.println("AS5600 not found. Check wiring!");
    while (1);
  }

  Serial.println("AS5600 Ready.");
}

void loop() {
  int angle = encoder.readAngle(); // returns value from 0 to 4095
  float degrees = (angle * 360.0) / 4096.0; // convert to degrees

  Serial.print("Raw: ");
  Serial.print(angle);
  Serial.print(" | Degrees: ");
  Serial.println(degrees);
  delay(200);
}
