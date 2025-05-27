#include <Zumo32U4.h>
#include <math.h>

const int fromNicla = 14;  // PB3 of andere digitale pin

void setup() {
  Serial.begin(9600);
  pinMode(fromNicla, INPUT_PULLUP);  // Zorgt voor stabiele input
}

bool waitForStartBit() {
  // Wacht op een geïnverteerde startbit: dus we wachten op 'LOW' (want Nicla stuurt '1')
  while (digitalRead(fromNicla) == HIGH) {
    delay(1);
  }
  delay(10);  // Stabilisatie
  return true;
}

bool receiveBit() {
  delay(10);  // Synchronisatie
  bool rawBit = digitalRead(fromNicla);
  return !rawBit;  // Inverteer het bit
}

byte receiveByte() {
  byte value = 0;
  for (int i = 0; i < 8; i++) {  // Van bit 0 naar bit 7 (LSB → MSB)
    bool bitVal = receiveBit();
    value |= (bitVal << i);  // i.p.v. (bitVal << (7 - i))
  }
  return value;
}

void loop() {
  byte ontvangen = '0';
  if (waitForStartBit()) {
    byte ontvangen = receiveByte();
    Serial.print("Ontvangen byte: ");
    Serial.println(ontvangen, BIN);
  }
  delay(10);
  


}
