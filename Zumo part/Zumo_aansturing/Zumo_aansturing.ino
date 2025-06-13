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

// Wiel aansturing
const int standaardSnelheid = 40;
const int langzaamSnelheid = 30;
const int snelSnelheid = 60;
const int stopSnelheid = 0;

const int correctieLinks = 5; //kleine correctie nodig, links is anders langzamer
const int correctieRechts = 0;
const int draaiSpeed = 50;

void setup() {
  pinMode(fromNicla, INPUT_PULLUP);
  Serial.begin(9600);

  // OLED initialisatie
  oled.init();             // Init de SH1106 OLED
  oled.setLayout8x2();     // Bepaal een 8×2 tekst-layout
  oled.clear();            // Maak het scherm leeg
  
  // Welkomstboodschap op OLED
  oled.gotoXY(0, 0);
  oled.print(F("Wachten op"));
  oled.gotoXY(0, 1);
  oled.print(F("Nicdata"));
  oled.display();          // Zet buffer op scherm
}

bool waitForStartBit() {
  unsigned long startTime = millis();
  const unsigned long WAIT_TIMEOUT = 50;

  while (millis() - startTime < WAIT_TIMEOUT) {
    if (digitalRead(fromNicla) == LOW) {
      delayMicroseconds(200); // Small debounce
      if (digitalRead(fromNicla) == LOW) {
        delayMicroseconds(9800);
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

// Helper functie om bewegingsstatus correct bij te houden
void setMovingState(byte actieCode) {
  // Beweging = alles behalve stop (92) en verkeersbord commando's (93-127)
  if (actieCode < 92) {
    isMoving = true;
  } else if (actieCode == 92) {
    isMoving = false;
  } else {
    // Verkeersbord commando's - kunnen zowel beweging als stop veroorzaken
    // We laten de individuele handlers dit bepalen
  }
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
    isMoving = false;  // Expliciet stoppen
    return;
  }

  currentCommand = actieCode;

  if (actieCode <= 92) {
    handleMovementCommand(actieCode);
    setMovingState(actieCode);  // Gebruik helper functie
  } else if (actieCode >= 93 && actieCode <= 127) {
    handleTrafficSignCommand(actieCode);
    // isMoving wordt door individuele traffic sign handlers gezet
  } else {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Onbekend:"));
    oled.gotoXY(0, 1);
    oled.print(actieCode);
    oled.display();
    motors.setSpeeds(0, 0);
    isMoving = false;  // Onbekend commando = stop
  }
}

void stuurLinks(){
  motors.setLeftSpeed(-draaiSpeed + correctieLinks);
  motors.setRightSpeed(draaiSpeed);
}

void stuurRechtdoor(){
  motors.setLeftSpeed(standaardSnelheid + correctieLinks);
  motors.setRightSpeed(standaardSnelheid + correctieRechts);
}

void stuurRechtdoorLangzaam(){
  motors.setLeftSpeed(langzaamSnelheid + correctieLinks);
  motors.setRightSpeed(langzaamSnelheid + correctieRechts);
}

void stuurRechtdoorSnel(){
  motors.setLeftSpeed(snelSnelheid + correctieLinks);
  motors.setRightSpeed(snelSnelheid + correctieRechts);
}

void stuurRechts(){
  motors.setLeftSpeed(draaiSpeed + correctieLinks);
  motors.setRightSpeed(-draaiSpeed);
}

void stuurAchteruit(){
  motors.setLeftSpeed(-standaardSnelheid + correctieLinks);
  motors.setRightSpeed(-standaardSnelheid);
}

void stuurStop(){
  motors.setLeftSpeed(stopSnelheid);
  motors.setRightSpeed(stopSnelheid);
}

void handleMovementCommand(byte actieCode) {
  // OLED updaten: toon de movement-code
  oled.clear();
  oled.gotoXY(0, 0);
  oled.print(F("Move:"));
  oled.print(actieCode);
  oled.display();

  // Scherp links
  if (actieCode < 10) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Draaien L"));
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(-draaiSpeed);
    oled.print(F("R:"));
    oled.print(draaiSpeed);
    oled.display();

    stuurLinks();
  }

  // Schuin links
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

  // Rijdt rechtdoor
  else if (actieCode == 45) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Rechtdoor"));
    oled.gotoXY(0, 1);
    oled.print(F("L:30R:30"));
    oled.display();

    stuurRechtdoor();
  }

  // Schuin rechts
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

  // Scherp rechts
  else if (actieCode <= 90) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Draaien R"));  // Fix: was "Draaien L"
    oled.gotoXY(0, 1);
    oled.print(F("L:"));
    oled.print(draaiSpeed);
    oled.print(F("R:"));
    oled.print(-draaiSpeed);
    oled.display();

    stuurRechts();
  }

  // Rijdt achteruit
  else if (actieCode == 91) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Achteruit"));
    oled.gotoXY(0, 1);
    oled.print(F("L:-30 R:-30"));
    oled.display();

    stuurAchteruit();
  }

  // Stop met rijden
  else if (actieCode == 92) {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Stop"));
    oled.gotoXY(0, 1);
    oled.print(F("L:0 R:0"));
    oled.display();

    stuurStop();
  }
  else {
    oled.clear();
    oled.gotoXY(0, 0);
    oled.print(F("Ongeldig"));
    oled.gotoXY(0, 1);
    oled.print(actieCode);
    oled.display();

    stuurStop();
  }
}

void handleTrafficSignCommand(byte actieCode) {
  motors.setSpeeds(0, 0);
  oled.clear();

  switch (actieCode) {
    // Voorrangs weg
    case 93:
      oled.gotoXY(0, 0);
      oled.print(F("Toegang OK"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:93"));
      
      stuurStop();
      isMoving = false;
      delay(3000);
      break;

    // Verboden toegang  
    case 94:
      oled.gotoXY(0, 0);
      oled.print(F("Verboden"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:94"));
      isMoving = false;
      break;

    // Verplicht links afslaan  
    case 95:
      oled.gotoXY(0, 0);
      oled.print(F("Verplicht links"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:95"));

      stuurRechtdoor();
      isMoving = true;  // We gaan bewegen
      delay(4000);

      stuurLinks();
      delay(1500);
      isMoving = false;  // Beweging klaar
      break;

     // Haaientand
    case 96:
      oled.gotoXY(0, 0);
      oled.print(F("Haaietand"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:96"));
      delay(1000);
      stuurStop();
      isMoving = false;
      delay(1000);
      break;

    // Snelheid 50km/h
    case 97:
      oled.gotoXY(0, 0);
      oled.print(F("50 km/h"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:97"));

      stuurRechtdoorSnel();
      isMoving = true;  // We gaan sneller bewegen
      delay(3000);
      isMoving = false;  // Beweging gedaan
      break;

    // Stop bord
    case 98:
      oled.gotoXY(0, 0);
      oled.print(F("STOP bord"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:98"));

      stuurStop();
      isMoving = false;
      delay(2000);
      break;

    // Groen stoplicht
    case 125:
      oled.gotoXY(0, 0);
      oled.print(F("GROEN"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:125"));

      stuurRechtdoor();
      isMoving = true;  // We gaan bewegen
      break;
    
    //Oranje stoplicht
    case 126:
      oled.gotoXY(0, 0);
      oled.print(F("GEEL"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:126"));
      
      stuurRechtdoor();
      isMoving = true;
      delay(1000);
      stuurStop();
      isMoving = false;
      delay(3000);
      stuurRechtdoor();
      isMoving = true;
      break;
    
    // Rood stoplicht
    case 127:
      oled.gotoXY(0, 0);
      oled.print(F("ROOD"));
      oled.gotoXY(0, 1);
      oled.print(F("Code:127"));

      stuurRechtdoor();
      isMoving = true;
      delay(1000);
      stuurStop();
      isMoving = false;
      delay(3000);
      stuurRechtdoor();
      isMoving = true;
      break;
    
    // Onbekend
    default:
      oled.gotoXY(0, 0);
      oled.print(F("Onbekend"));
      oled.gotoXY(0, 1);
      oled.print(actieCode);
      isMoving = false;
      break;
  }
  oled.display();
}

void loop() {
  static byte opslagarray[3] = {255, 255, 255}; // initialiseer met onmogelijke waarde
  static byte lastCode = 255; // onmogelijke startwaarde
  static bool allowed = false;
  static bool stableCodeIsUnder10 = false;

  if (waitForStartBit()) {
    byte receivedCode = receiveByte();
    Serial.print(F("Ontvangen byte: "));
    Serial.println(receivedCode, DEC);

    lastCommandTime = millis();// start de millis elke loop

    if (receivedCode != lastCode) {
      if (allowed && receivedCode > 10 || stableCodeIsUnder10 && allowed) {
        interpretCommand(receivedCode);
        lastCode = receivedCode;
        allowed = false; // reset
      }
      else if (receivedCode <= 10 && receivedCode >= 0 ) {
        // soms krijgt de zumo een 0 of een 1 binnen terwijl deze ongewenst is.
        // dus dit zorgt ervoor dat de waardes stabiel moeten zijn voordat het geaccepteerd wordt.
        // schuif waarden naar rechts
        opslagarray[2] = opslagarray[1];
        opslagarray[1] = opslagarray[0];
        opslagarray[0] = receivedCode;

        // check of alle 3 waardes gelijk zijn
        if (opslagarray[0] == opslagarray[1] && opslagarray[1] == opslagarray[2]) {
          allowed = true;
          stableCodeIsUnder10 = true;
        } else {
          // stop commando zodat het signaal stabiel kan worden.
          interpretCommand(92);
          isMoving = false;  // Expliciet stoppen na stop commando
          allowed = false;
        }
      }
      else{
        // reset opslagarray
        opslagarray[0] = opslagarray[1] = opslagarray[2] = 255;
        allowed = true;
        stableCodeIsUnder10 = false;
      }
    }
  }  
  
  // Verbeterde timeout check - checkt ook of er überhaupt commando's zijn ontvangen
  if (millis() - lastCommandTime > 1500) {
    // Check of we in een bewegingstoestand zitten EN er is een timeout
    if (isMoving || (currentCommand >= 0 && currentCommand < 92) || currentCommand == 125 || currentCommand == 126 || currentCommand == 127) {
      // Stop de motoren
      stuurStop();
      oled.clear();
      oled.gotoXY(0, 0);
      oled.print(F("Timeout"));
      oled.gotoXY(0, 1);
      oled.print(F("Wachten..."));
      oled.display();

      isMoving = false;
      currentCommand = 92;
    }
  }
  else {
    delay(8); // korte delay
  }
}