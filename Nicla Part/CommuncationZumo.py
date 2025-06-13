import time
from machine import Pin

to_zumo = Pin("PA9", Pin.OUT_PP)

def send_code(code):
    # 1. Startbit sturen (hoog)
    to_zumo.value(1)
    time.sleep_ms(10)

    # 2. Verzend de 8 databitjes (MSB → LSB)
    for i in range(7, -1, -1):
        bit = (code >> i) & 1
        to_zumo.value(bit)
        time.sleep_ms(10)

    # 3. Na afloop: lijn weer laag
    to_zumo.value(0)

while True:
    send_code(0b00101101)  # Voorbeeldbyte
    time.sleep(1)  # Wacht even voor volgende verzending
