#include <Zumo32U4.h>

Zumo32U4Motors motors;
Zumo32U4LCD lcd;

const int fromNicla = 14;  // Pas aan naar juiste pin op de Zumo

byte lastCode = 255; // Onmogelijk initieel getal zodat de eerste byte altijd verwerkt wordt

void setup() {
  pinMode(fromNicla, INPUT_PULLUP);
  lcd.clear();
  Serial.begin(9600);
}

bool waitForStartBit() {
  // Startbit op Nicla is 1, dus Zumo leest LOW
  while (digitalRead(fromNicla) == HIGH) {
    delay(1);
  }
  delay(10);  // Stabilisatie
  return true;
}

bool receiveBit() {
  delay(10);
  return !digitalRead(fromNicla);  // Inversie van het signaal
}

byte receiveByte() {
  byte value = 0;
  for (int i = 0; i < 8; i++) {
    bool bitVal = receiveBit();
    value |= (bitVal << i);
  }
  return value;
}

void interpretCommand(byte code) {
  bool noodstop = (code & 0b10000000) >> 7;
  byte actieCode = code & 0b01111111;

  lcd.clear();
  Serial.print("Ontvangen byte: ");
  Serial.println(code, BIN);  // Print binaire vorm

  if (noodstop) {
    lcd.print("NOODSTOP!");
    motors.setSpeeds(0, 0);
    return;
  }

  switch (actieCode) {
    case 0 ... 90: // code voor besturing zumo
      if (actieCode < 45) {
        // Langzaam naar rechts
        int verschil = 45 - actieCode;
        int snelheidLinks = 50;
        int snelheidRechts = 50 - verschil;  // Rechts motor langzamer

        // Minimale snelheid ondergrens
        if (snelheidRechts < 20) snelheidRechts = 20;

        lcd.print("Rechts:");
        lcd.print(actieCode);
        motors.setSpeeds(snelheidLinks, snelheidRechts);
      }
      else if (actieCode == 45) {
        // Rechtdoor
        lcd.print("Rechtdoor");
        motors.setSpeeds(50, 50);
      }
      else if (actieCode > 45) {
        // Langzaam naar links
        int verschil = actieCode - 45;
        int snelheidLinks = 50 - verschil;   // Links motor langzamer
        int snelheidRechts = 50;

        if (snelheidLinks < 20) snelheidLinks = 20;

        lcd.print("Links:");
        lcd.print(actieCode);
        motors.setSpeeds(snelheidLinks, snelheidRechts);
      }
      break;
    case 91:
      lcd.print("Achteruit");
      motors.setSpeeds(-50, -50);
      break;
    case 92:
      lcd.print("Stop");
      motors.setSpeeds(0, 0);
      break;
    case 121 ... 124:
      lcd.print("Bord:");
      lcd.gotoXY(0, 1);
      lcd.print(actieCode);
      break;
    case 125 ... 127:
      lcd.print("Stoplicht:");
      lcd.gotoXY(0, 1);
      lcd.print(actieCode);
      break;
    default:
      lcd.print("Onbekend:");
      lcd.gotoXY(0, 1);
      lcd.print(actieCode);
      motors.setSpeeds(0, 0);
      break;
  }
}

void loop() {
  if (!waitForStartBit()) return;

  byte currentCode = receiveByte();

  if (currentCode != lastCode) {
    interpretCommand(currentCode);
    lastCode = currentCode;
  }
}
