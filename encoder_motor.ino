const int encoderPinA = 34;
const int encoderPinB = 35;

void setup() {
  Serial.begin(115200);
  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);
}

void loop() {
  int A = digitalRead(encoderPinA);
  int B = digitalRead(encoderPinB);

  Serial.print("A: ");
  Serial.print(A);
  Serial.print(" | B: ");
  Serial.println(B);

  delay(100);  // 10 readings per second
}
