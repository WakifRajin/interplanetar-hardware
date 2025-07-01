volatile long encoderCount = 0;
const int encoderPinA = 34;  // Channel A
const int encoderPinB = 35;  // Channel B

void IRAM_ATTR handleEncoderA() {
  // Read channel B to determine rotation direction
  if (digitalRead(encoderPinB) == HIGH) {
    encoderCount++;
  } else {
    encoderCount--;
  }
}

void setup() {
  Serial.begin(115200);
  
  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(encoderPinA), handleEncoderA, RISING);
}

void loop() {
  static long lastCount = 0;

  if (lastCount != encoderCount) {
    Serial.print("Encoder Count: ");
    Serial.println(encoderCount);
    lastCount = encoderCount;
  }

  delay(50); // Adjust for responsiveness
}
