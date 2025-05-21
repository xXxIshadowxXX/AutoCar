import time
from machine import Pin

# Gebruik P0 als output naar Zumo, P1 als input van Zumo
to_zumo = Pin("PA9", Pin.OUT_PP)
from_zumo = Pin("PA10", Pin.IN)

# De byte die je wilt sturen
command_code = 0xAB

def send_bit(bit):
    to_zumo.value(bit)
    time.sleep_ms(10)

def receive_bit():
    time.sleep_ms(10)
    return from_zumo.value()

def send_byte(byte):
    for i in range(7, -1, -1):  # MSB first
        bit = (byte >> i) & 1
        send_bit(bit)

def receive_byte():
    val = 0
    for i in range(7, -1, -1):
        bit = receive_bit()
        val |= (bit << i)
    return val

def send_code(code):
    print("Wachten op klaar Zumo...")
    # Stap 1: Wacht tot Zumo klaar is met luisteren
    while from_zumo.value() == 0:
        time.sleep_ms(10)

    # Stap 2: Stuur startpuls
    to_zumo.value(1)
    time.sleep_ms(100)
    to_zumo.value(0)
    print("Startpuls verzonden.")

    # Stap 3: Stuur de 8 bits van de code
    send_byte(code)
    print("Code verzonden:", hex(code))

    # Stap 4: Wacht op echo van Zumo
    echo = receive_byte()
    print("Echo ontvangen:", hex(echo))

    # Stap 5: Bevestig of echo klopt
    if echo == code:
        print("Code OK - verstuur ACK")
        send_bit(1)  # ACK
    else:
        print("Code MISMATCH - verstuur NAK")
        send_bit(0)  # NAK

while True:
    send_code(command_code)
    time.sleep(5)  # Wacht 5 seconden voordat volgende code wordt verstuurd
