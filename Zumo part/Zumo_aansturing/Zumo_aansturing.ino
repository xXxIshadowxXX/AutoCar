#include <Zumo32U4OLED.h>  // OLED-klasse include
#include <Zumo32U4.h>

Zumo32U4OLED oled;          // OLED instance
Zumo32U4Motors motors;

const int fromNicla = 14;
byte lastCode = 255;
byte currentCommand = 92;
bool isMoving = false;
unsigned long lastCommandTime = 0;
const unsigned long COMMAND_TIMEOUT = 2000;

void setup() {
  pinMode(fromNicla, INPUT_PULLUP);
  Serial.begin(9600);

  // OLED initialisatie
  oled.init();             // Init de SH1106 OLED :contentReference[oaicite:4]{index=4}
  oled.setLayout8x2();     // Bepaal een 8×2 tekst-layout :contentReference[oaicite:5]{index=5}
  oled.clear();            // Maak het scherm leeg
  
  // Welkomstboodschap op OLED
  oled.gotoXY(0, 0);
  oled.print(F("Wachten op"));
  oled.gotoXY(0, 1);
  oled.print(F("Nicdata"));
  oled.display();          // Zet buffer op scherm :contentReference[oaicite:6]{index=6}
}

bool waitForStartBit() {
  unsigned long startTime = millis();
  const unsigned long WAIT_TIMEOUT = 50;

  while (millis() - startTime < WAIT_TIMEOUT) {
    if (digitalRead(fromNicla) == LOW) {
      delayMicroseconds(10000); // Small debounce
      if (digitalRead(fromNicla) == LOW) {
        return true; // Confirmed start bit
      }
    }
    delayMicroseconds(100);  // Reduce CPU usage
  }
  return false;
}

bool receiveBit() {
  delayMicroseconds(10000); // Small debounce
  return !digitalRead(fromNicla);
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

  // OLED updaten: duidelijk maken welke byte binnenkomt
  oled.clear();
  oled.gotoXY(0, 0);
  oled.print(F("Byte:"));
  oled.print(code, BIN);
  oled.gotoXY(0, 1);
  oled.print(noodstop ? F("Noodstop") : F("Actie:"));
  oled.print(actieCode);
  oled.display();  // Zorg dat het buffer zichtbaar wordt

  lastCommandTime = millis();

  if (noodstop) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("NOODSTOP!"));
    oled.gotoXY(0, 1);
    oled.print(F("Motoren UIT"));
    oled.display();
    motors.setSpeeds(0, 0);
    currentCommand = 92;
    isMoving = false;
    return;
  }

  currentCommand = actieCode;

  if (actieCode <= 92) {
    handleMovementCommand(actieCode);
    isMoving = (actieCode != 92);
  } else if (actieCode >= 93 && actieCode <= 127) {
    handleTrafficSignCommand(actieCode);
    isMoving = false;
  } else {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Onbekend:"));
    oled.gotoXY(0, 1);
    oled.print(actieCode);
    oled.display();
    motors.setSpeeds(0, 0);
    isMoving = false;
  }
}

void handleMovementCommand(byte actieCode) {
  const int standaardSnelheid = 40;
  const int correctieLinks = 5;
  const int correctieRechts = 0;

  // OLED updaten: toon de movement-code
  oled.clear();
  oled.gotoXY(0, 0);
  oled.print(F("Move:"));
  oled.print(actieCode);
  oled.display();

  if (actieCode < 10) {
    int draaiSpeed = 50;
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Draaien L"));
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(-draaiSpeed);
    oled.print(F("R:"));
    oled.print(draaiSpeed);
    oled.display();

    motors.setLeftSpeed(-draaiSpeed + correctieLinks);
    motors.setRightSpeed(draaiSpeed);
  }
  else if (actieCode <= 44) {
    int verschil = 45 - actieCode;
    int snelheidLinks = standaardSnelheid - verschil * 1.5;
    int snelheidRechts = standaardSnelheid;

    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Schuin L"));
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(snelheidLinks + correctieLinks);
    oled.print(F("R:"));
    oled.print(snelheidRechts);
    oled.display();

    motors.setLeftSpeed(snelheidLinks + correctieLinks);
    motors.setRightSpeed(snelheidRechts + correctieRechts);
  }
  else if (actieCode == 45) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Rechtdoor"));
    oled.gotoXY(0, 1);
    oled.print(F("L:30R:30"));
    oled.display();

    motors.setLeftSpeed(standaardSnelheid + correctieLinks);
    motors.setRightSpeed(standaardSnelheid + correctieRechts);
  }
  else if (actieCode <= 80) {
    int verschil = actieCode - 45;
    int snelheidLinks = standaardSnelheid;
    int snelheidRechts = standaardSnelheid - verschil * 1.5;

    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Schuin R"));
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(snelheidLinks + correctieLinks);
    oled.print(F("R:"));
    oled.print(snelheidRechts);
    oled.display();

    motors.setLeftSpeed(snelheidLinks + correctieLinks);
    motors.setRightSpeed(snelheidRechts + correctieRechts);
  }
  else if (actieCode <= 90) {
    int draaiSpeed = 50;
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Draaien L"));
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(draaiSpeed);
    oled.print(F("R:"));
    oled.print(-draaiSpeed);
    oled.display();

    motors.setLeftSpeed(draaiSpeed + correctieLinks);
    motors.setRightSpeed(-draaiSpeed);
  }
  else if (actieCode == 91) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Achteruit"));
    oled.gotoXY(0, 1);
    oled.print(F("L:-30 R:-30"));
    oled.display();

    motors.setLeftSpeed(-standaardSnelheid + correctieLinks);
    motors.setRightSpeed(-standaardSnelheid);
  }
  else if (actieCode == 92) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Stop"));
    oled.gotoXY(0, 1);
    oled.print(F("L:0 R:0"));
    oled.display();

    motors.setLeftSpeed(0);
    motors.setRightSpeed(0);
  }
  else {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Ongeldig"));
    oled.gotoXY(0, 1);
    oled.print(actieCode);
    oled.display();

    motors.setLeftSpeed(0);
    motors.setRightSpeed(0);
  }
}

void handleTrafficSignCommand(byte actieCode) {
  motors.setSpeeds(0, 0);
  oled.clear();

  const int standaardSnelheid = 40;
  const int correctieLinks = 5;

  const int snelheidLinks = standaardSnelheid + correctieLinks;
  const int snelheidRechts = standaardSnelheid;
  const int draaiSnelheid = standaardSnelheid + 10;

  switch (actieCode) {
    case 93:
      oled.gotoXY(0, 0);
      oled.print(F("Toegang OK"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:93"));
      break;
    case 94:
      oled.gotoXY(0, 0);
      oled.print(F("Verboden"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:94"));
      break;
    case 95:
      oled.gotoXY(0, 0);
      oled.print(F("Verplicht links"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:95"));
      motors.setSpeeds(standaardSnelheid, standaardSnelheid);// rechtdoor
      delay(1000);
      motors.setLeftSpeed(-draaiSnelheid);
      motors.setRightSpeed(draaiSnelheid);
      delay(1000);
      break;
    case 96:
      oled.gotoXY(0, 0);
      oled.print(F("Haaietand"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:96"));
      break;
    case 97:
      oled.gotoXY(0, 0);
      oled.print(F("50 km/h"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:97"));
      break;
    case 98:
      oled.gotoXY(0, 0);
      oled.print(F("STOP bord"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:98"));
      break;
    case 125:
      oled.gotoXY(0, 0);
      oled.print(F("GROEN"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:125"));
      break;
    case 126:
      oled.gotoXY(0, 0);
      oled.print(F("GEEL"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:126"));
      break;
    case 127:
      oled.gotoXY(0, 0);
      oled.print(F("ROOD"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:127"));
      break;
    default:
      oled.gotoXY(0, 0);
      oled.print(F("Onbekend"));
      oled.gotoXY(0, 1);
      oled.print(actieCode);
      break;
  }
  oled.display();
}

void executeCurrentCommand() {
  if (currentCommand <= 92) {
    handleMovementCommand(currentCommand);
  }
  else if (currentCommand > 92){
    handleTrafficSignCommand(currentCommand);
  }
}

void loop() {
  static byte opslagarray[3] = {0};
  static byte lastCode = 0;
  static bool allowed = false;

  if (waitForStartBit()) {
    byte receivedCode = receiveByte();
    Serial.print(F("Ontvangen byte: "));
    Serial.println(receivedCode, DEC);

    if (receivedCode != lastCode) {
      if (allowed) {
        interpretCommand(receivedCode);
        lastCode = receivedCode;
        allowed = false; // reset
      }
      else if (receivedCode <= 10 && receivedCode >= 0 || receivedCode >= 80 && receivedCode <= 90 ) {
        // soms krijgt de zumo een 0 of een 1 binnen terwijl deze ongewenst is.
        // dus dit zorgt ervoor dat de waardes stabiel moeten zijn voordat het geaccepteerd wordt.
        // schuif waarden naar rechts
        for (int i = 2; i > 0; i--) {
          opslagarray[i] = opslagarray[i - 1];
        }
        opslagarray[0] = receivedCode;

        // check of alle 3 waardes gelijk zijn
        if (opslagarray[0] == opslagarray[1] && opslagarray[1] == opslagarray[2]) {
          allowed = true;
        } else {
          allowed = false;
        }
      }
      else{
        // voor alle andere waardes van recieveCode
        allowed = true;
      }
    }
  } else {
    delay(10);
  }
  

  if (isMoving) {
    executeCurrentCommand();
  }
}
