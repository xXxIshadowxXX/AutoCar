  #include <Wire.h>
  #include <Zumo32U4.h>
  #include <math.h>

  //constants for the connection with the Zumo Board
  Zumo32U4Motors motors;
  Zumo32U4ButtonA buttonA;
  Zumo32U4ButtonB buttonB;
  Zumo32U4ButtonC buttonC;

  // communcation ports for the Zumo I/O
  const int toNicla = 13;
  const int fromNicla = 14;

  void setup()
  {
    // Uncomment indien nodig om richting motoren te corrigeren:
    // motors.flipLeftMotor(true);
    // motors.flipRightMotor(true);

    pinMode(toNicla, OUTPUT);
    pinMode(fromNicla, INPUT_PULLUP);

    ledYellow(0); // Zorg dat LED uit staat
  }

  int recieveCode() {
    static int currentProtocol = 0;
    static int completedCode = 0;

    switch(currentProtocol) {
      case 0:
        // Stap 1: Wachten op start van communicatie van Nicla
        if (digitalRead(fromNicla) == HIGH) {
          digitalWrite(toNicla, HIGH);  // Bevestig ontvangst
          delay(100);                   // Wacht even
          currentProtocol = 1;
        }
        break;

      case 1:
        // Stap 2: Wachten op code bits van Nicla
        completedCode = 0;
        for (int i = 0; i < 8; i++) {
          delay(10); // wacht op bit
          int bit = digitalRead(fromNicla);
          completedCode |= (bit << (7 - i));
        }
        currentProtocol = 2;
        break;

      case 2:
        // Stap 3: Stuur ontvangen code terug naar Nicla voor sync
        for (int i = 7; i >= 0; i--) {
          int bit = (completedCode >> i) & 1;
          digitalWrite(toNicla, bit);
          delay(10);
        }
        currentProtocol = 3;
        break;

      case 3:
        // Stap 4: Wachten op ACK (1 = correct, 0 = fout)
        if (digitalRead(fromNicla) == HIGH) {
          digitalWrite(toNicla, HIGH);  // afsluiting
          delay(200);
          currentProtocol = 0;
          return completedCode;         // correcte code ontvangen
        } else {
          // Code was fout → opnieuw ontvangen
          currentProtocol = 1;
        }
        break;
    }
    Serial.print("\n de code van de current protocol = ");
    Serial.print(currentProtocol);
    Serial.print("\n de code van de completed code   = ");
    Serial.print(completedCode);
    return -1; // nog geen volledige code ontvangen
  }


  void loop()
  {
    int temp = recieveCode();
    if (buttonA.isPressed())
    {
      delay(1000);// zorgen dat het niet gelijk door rijdt wanneer je knop indrukt
      // Vooruit rijden
      ledYellow(1);
      motors.setLeftSpeed(150);
      motors.setRightSpeed(150);
      delay(2500);
      motors.setLeftSpeed(0);
      motors.setRightSpeed(0);
      ledYellow(0);
    }
    else if (buttonB.isPressed())
    {
      delay(1000);// zorgen dat het niet gelijk door rijdt wanneer je knop indrukt
      // Rechts draaien (linkermotor vooruit, rechtermotor achteruit)
      motors.setLeftSpeed(150);
      motors.setRightSpeed(-150);
      delay(375);
      motors.setLeftSpeed(0);
      motors.setRightSpeed(0);
    }
    else if (buttonC.isPressed())
    {
      delay(1000);// zorgen dat het niet gelijk door rijdt wanneer je knop indrukt
      // Links draaien (linkermotor achteruit, rechtermotor vooruit)
      motors.setLeftSpeed(-150);
      motors.setRightSpeed(150);
      delay(375);
      motors.setLeftSpeed(0);
      motors.setRightSpeed(0);
    }

    delay(100); // kleine vertraging om stuiteren van knop te vermijden
  }
