volatile long encoderCount = 0;

const int encoderPinA = 2;  // Must be interrupt pin
const int encoderPinB = 3;  // B is just read inside ISR

void setup() {
  Serial.begin(9600);  // You can use 115200 if preferred

  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);

  // Attach interrupt to encoder A (D2 = INT0 on Nano)
  attachInterrupt(digitalPinToInterrupt(encoderPinA), handleEncoder, RISING);
}

void loop() {
  static long lastCount = 0;

  if (lastCount != encoderCount) {
    Serial.print("Encoder Count: ");
    Serial.println(encoderCount);
    lastCount = encoderCount;
  }

  delay(50);  // Slow enough to observe
}

void handleEncoder() {
  // Read B to determine direction
  if (digitalRead(encoderPinB) == HIGH) {
    encoderCount++;
  } else {
    encoderCount--;
  }
}
