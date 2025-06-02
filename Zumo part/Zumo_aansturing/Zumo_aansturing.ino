#include <Zumo32U4.h>

Zumo32U4Motors motors;
Zumo32U4LCD lcd;

const int fromNicla = 14;  // Pin voor communicatie met Nicla
byte lastCode = 255;       // Onmogelijk initieel getal zodat de eerste byte altijd verwerkt wordt
byte currentCommand = 92;  // Start met stop commando
bool isMoving = false;
unsigned long lastCommandTime = 0;
const unsigned long COMMAND_TIMEOUT = 2000;  // 2 seconden timeout

void setup() {
  pinMode(fromNicla, INPUT_PULLUP);
  lcd.clear();
  Serial.begin(9600);
  lcd.print("Wachten op");
  lcd.gotoXY(0, 1);
  lcd.print("Nicla data...");
}

bool waitForStartBit() {
  // Non-blocking check voor startbit
  unsigned long startTime = millis();
  const unsigned long WAIT_TIMEOUT = 50;  // 50ms timeout

  while (digitalRead(fromNicla) == HIGH) {
    if (millis() - startTime > WAIT_TIMEOUT) {
      return false;  // Timeout, geen startbit gevonden
    }
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
  // Check noodstop bit (bit 7)
  bool noodstop = (code & 0b10000000) >> 7;
  byte actieCode = code & 0b01111111;  // Onderste 7 bits

  lcd.clear();
  Serial.print("Ontvangen byte: ");
  Serial.println(code, BIN);  // Print binaire vorm
  Serial.print("Noodstop: ");
  Serial.println(noodstop ? "JA" : "NEE");
  Serial.print("Actie code: ");
  Serial.println(actieCode);

  // Update laatste commando tijd
  lastCommandTime = millis();

  // Noodstop heeft altijd voorrang
  if (noodstop) {
    lcd.print("NOODSTOP!");
    lcd.gotoXY(0, 1);
    lcd.print("Motoren UIT");
    motors.setSpeeds(0, 0);
    currentCommand = 92;  // Stop commando
    isMoving = false;
    return;
  }

  // Sla het commando op
  currentCommand = actieCode;

  // Interpreteer commando op basis van actieCode
  if (actieCode >= 0 && actieCode <= 92) {
    // Besturingscommando's
    handleMovementCommand(actieCode);
    isMoving = (actieCode != 92);  // Als het niet stop is, dan bewegen we
  } else if (actieCode >= 93 && actieCode <= 127) {
    // Verkeersborden en signalering
    handleTrafficSignCommand(actieCode);
    isMoving = false;  // Stop bij verkeersborden
  } else {
    // Onbekend commando
    lcd.print("Onbekend:");
    lcd.gotoXY(0, 1);
    lcd.print(actieCode);
    motors.setSpeeds(0, 0);
    isMoving = false;
  }
}

void handleMovementCommand(byte actieCode) {
  Serial.print("Movement command: ");
  Serial.println(actieCode);

  if (actieCode >= 0 && actieCode < 10) {
    // Scherpe bocht links - draaien over eigen as
    int draaispeed = 70;  // Vaste snelheid voor draaien

    lcd.print("Draai Rechts");
    lcd.gotoXY(0, 1);
    lcd.print("R:");
    lcd.print(draaispeed);
    lcd.print(" L:");
    lcd.print(-draaispeed);

    Serial.print("Draai Rechts - Rechts: ");
    Serial.print(draaispeed);
    Serial.print(", Links: ");
    Serial.println(-draaispeed);

    motors.setSpeeds(-draaispeed, draaispeed);  // links achteruit, rechts vooruit
  } else if (actieCode >= 10 && actieCode <= 44) {
    // Langzaam naar rechts (10-44)
    int verschil = 45 - actieCode;
    int snelheidLinks = 50;
    int snelheidRechts = 50 - verschil;  // Rechts motor langzamer

    // Minimale snelheid ondergrens
    if (snelheidRechts < 20) snelheidRechts = 20;

    lcd.print("Rechts: ");
    lcd.print(actieCode);
    lcd.gotoXY(0, 1);
    lcd.print("R:");
    lcd.print(snelheidRechts);
    lcd.print(" L:");
    lcd.print(snelheidLinks);

    Serial.print("Rechts - Rechts: ");
    Serial.print(snelheidRechts);
    Serial.print(", Links: ");
    Serial.println(snelheidLinks);

    motors.setSpeeds(snelheidLinks, snelheidRechts);  // Gecorrigeerde volgorde
  } else if (actieCode == 45) {
    // Rechtdoor
    lcd.print("Rechtdoor");
    lcd.gotoXY(0, 1);
    lcd.print("R:50 L:50");

    Serial.println("Rechtdoor - Rechts: 50, Links: 50");
    motors.setSpeeds(50, 50);  // Beide motors vooruit
  } else if (actieCode >= 46 && actieCode <= 80) {
    // Langzaam naar links (46-80)
    int verschil = actieCode - 45;
    int snelheidLinks = 50 - verschil;  // Links motor langzamer
    int snelheidRechts = 50;

    // Minimale snelheid ondergrens
    if (snelheidLinks < 20) snelheidLinks = 20;

    lcd.print("Links: ");
    lcd.print(actieCode);
    lcd.gotoXY(0, 1);
    lcd.print("R:");
    lcd.print(snelheidRechts);
    lcd.print(" L:");
    lcd.print(snelheidLinks);

    Serial.print("Links - Rechts: ");
    Serial.print(snelheidRechts);
    Serial.print(", Links: ");
    Serial.println(snelheidLinks);

    motors.setSpeeds(snelheidLinks,snelheidRechts );  // Gecorrigeerde volgorde
  } else if (actieCode > 80 && actieCode <= 90) {
    // Scherpe bocht links - draaien over eigen as
    int draaispeed = 70;  // Vaste snelheid voor draaien

    lcd.print("Draai Links");
    lcd.gotoXY(0, 1);
    lcd.print("R:");
    lcd.print(-draaispeed);
    lcd.print(" L:");
    lcd.print(draaispeed);

    Serial.print("Draai Links - Rechts: ");
    Serial.print(-draaispeed);
    Serial.print(", Links: ");
    Serial.println(draaispeed);

    motors.setSpeeds(draaispeed, -draaispeed);  // links vooruit, Rechts achteruit 
  } else if (actieCode == 91) {
    lcd.print("Achteruit");
    lcd.gotoXY(0, 1);
    lcd.print("R:-50 L:-50");

    Serial.println("Achteruit - Rechts: -50, Links: -50");
    motors.setSpeeds(-50, -50);  // Beide motors achteruit
  } else if (actieCode == 92) {
    lcd.print("Stop");
    lcd.gotoXY(0, 1);
    lcd.print("R:0 L:0");

    Serial.println("Stop - Rechts: 0, Links: 0");
    motors.setSpeeds(0, 0);  // Beide motors stoppen
  } else {
    lcd.print("Ongeldig mov:");
    lcd.gotoXY(0, 1);
    lcd.print(actieCode);

    Serial.print("Ongeldig bewegingscommando: ");
    Serial.println(actieCode);
    motors.setSpeeds(0, 0);
  }
}

void handleTrafficSignCommand(byte actieCode) {
  // Stop motoren bij verkeersbord detectie
  motors.setSpeeds(0, 0);

  switch (actieCode) {
    case 93:
      lcd.print("Toegang geven");
      lcd.gotoXY(0, 1);
      lcd.print("Bord: ");
      lcd.print(actieCode);
      break;

    case 94:
      lcd.print("Verboden");
      lcd.gotoXY(0, 1);
      lcd.print("Toegang: ");
      lcd.print(actieCode);
      break;

    case 95:
      lcd.print("Eenrichting");
      lcd.gotoXY(0, 1);
      lcd.print("Bord: ");
      lcd.print(actieCode);
      break;

    case 96:
      lcd.print("Haaietand");
      lcd.gotoXY(0, 1);
      lcd.print("Bord: ");
      lcd.print(actieCode);
      break;

    case 97:
      lcd.print("50 km/h bord");
      lcd.gotoXY(0, 1);
      lcd.print("Code: ");
      lcd.print(actieCode);
      break;

    case 98:
      lcd.print("STOP bord");
      lcd.gotoXY(0, 1);
      lcd.print("Code: ");
      lcd.print(actieCode);
      break;

    case 125:
      lcd.print("GROEN");
      lcd.gotoXY(0, 1);
      lcd.print("stoplicht: ");
      lcd.print(actieCode);
      break;

    case 126:
      lcd.print("GEEL");
      lcd.gotoXY(0, 1);
      lcd.print("stoplicht: ");
      lcd.print(actieCode);
      break;

    case 127:
      lcd.print("ROOD");
      lcd.gotoXY(0, 1);
      lcd.print("stoplicht: ");
      lcd.print(actieCode);
      break;

    default:
      lcd.print("Onbekend bord:");
      lcd.gotoXY(0, 1);
      lcd.print(actieCode);
      break;
  }
}

void executeCurrentCommand() {
  // Voer het huidige commando uit (voor continue beweging)
  if (currentCommand >= 0 && currentCommand <= 92) {
    handleMovementCommand(currentCommand);
  }
}

void loop() {
  // Probeer nieuwe data te ontvangen (non-blocking)
  if (waitForStartBit()) {
    byte receivedCode = receiveByte();
    Serial.print("Ontvangen byte: ");
    Serial.println(receivedCode, DEC);

    // Alleen verwerken als de code anders is dan de vorige
    if (receivedCode != lastCode) {
      interpretCommand(receivedCode);
      lastCode = receivedCode;
    }
  }

  // Voer het huidige commando uit als we aan het bewegen zijn
  if (isMoving && currentCommand >= 0 && currentCommand <= 92) {
    // Heruitvoeren van bewegingscommando voor continue beweging
    executeCurrentCommand();
  }

  delay(10);  // Kleine delay om de loop niet te snel te laten draaien
}