import sensor, image, time
import network, socket
from pyb import LED
from machine import Pin

SSID = "CarGalss"
KEY = "Kuijpers"
PORT = 80
to_zumo = Pin("PA9", Pin.OUT_PP)

# Camera instellen
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

LED(1).off()  # Rood
LED(2).on()   # Groen = verbindend

# WiFi connectie
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, KEY)

print("Verbinden...")
for i in range(30):
    if wlan.isconnected():
        break
    LED(2).toggle()
    time.sleep_ms(500)

LED(2).off()
LED(1).on()
ip = wlan.ifconfig()[0]
print("Verbonden:", ip)

# Server
addr = socket.getaddrinfo("0.0.0.0", PORT)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
print("HTTP-server actief op: http://%s:%d" % (ip, PORT))

waarde = 45

def send_all(client, data):
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)  # converteer altijd naar bytes
    while data:
        sent = client.send(data)
        data = data[sent:]


def send_code(code):
    to_zumo.value(1)
    time.sleep_ms(10)
    for i in range(8):
        time.sleep_ms(10)
        to_zumo.value((code >> i) & 1)
    to_zumo.value(0)

while True:
    client, addr = s.accept()
    req = client.recv(256)
    req = str(req)

    if "/getphoto" in req:
        img = sensor.snapshot().rotation_corr(z_rotation=180)
        jpeg = img.compress(quality=50)
        client.send("HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\n\r\n")
        send_all(client, jpeg)

    if "/setwaarde?val=" in req:
        try:
            val = int(req.split("val=")[1].split()[0].split("&")[0])
            waarde = val
            send_code(val)  # <-- DIRECT DOORSTUREN
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nWaarde ontvangen: %d" % waarde)
            print(waarde)
        except:
            client.send("HTTP/1.1 400 Bad Request\r\n\r\n")

    elif "/approve" in req:
        LED(3).on()
        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")
        LED(3).off()

    client.close()
