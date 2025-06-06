import sensor, image, time
import network, socket
from pyb import LED
from machine import Pin

# === Config ===
SSID = "CarGalss"
KEY = "Kuijpers"
PORT = 80
to_zumo = Pin("PA9", Pin.OUT_PP)

# === Setup camera ===
print("Skibedi")
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

# === LEDs voor status ===
LED(1).off()  # Rood
LED(2).on()   # Groen = nog niet verbonden

# === Verbinden met WiFi ===
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, KEY)

# Verbinding met timeout
connect_attempts = 0
max_attempts = 30  # 15 seconden timeout

# Scan voor beschikbare netwerken (debug)
print("Scannen naar netwerken...")
try:
    networks = wlan.scan()
    print("Gevonden netwerken:")
    for net in networks:
        print(" -", net[0].decode('utf-8'), "- Signal:", net[3])
except:
    print("Scan mislukt")

print(f"Verbinden met: {SSID}")
wlan.connect(SSID, KEY)

while not wlan.isconnected() and connect_attempts < max_attempts:
    time.sleep_ms(500)
    connect_attempts += 1
    print(f"Verbinden... poging {connect_attempts}/{max_attempts}")

    # Blink LED tijdens verbinden
    if connect_attempts % 2 == 0:
        LED(2).on()
    else:
        LED(2).off()

LED(2).off()
LED(1).on()  # Verbonden
ip = wlan.ifconfig()[0]
print("Verbonden met IP:", ip)

# === Socket server setup ===
addr = socket.getaddrinfo("0.0.0.0", PORT)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
print("HTTP-server actief op: http://%s:%d" % (ip, PORT))

buffered_image = None

def send_all(client, data):
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)  # of bytearray(data)
    length = len(data)
    sent = 0
    while sent < length:
        sent += client.send(data[sent:])

def send_code(code):
    # 1. Startbit sturen (hoog)
    to_zumo.value(1)
    time.sleep_ms(10)

    # 2. Verzend de 8 databitjes (MSB → LSB)
    for i in range(8):  # LSB → MSB
        bit = (code >> i) & 1
        to_zumo.value(bit)
        time.sleep_ms(10)

    # 3. Na afloop: lijn weer laag
    to_zumo.value(0)


# Maak bij start 1x een foto
print("Initieel foto maken...")
img = sensor.snapshot()
img.rotation_corr(z_rotation=180)
buffered_image = img.compress(quality=60)
waarde = 45

while True:
    client, addr = s.accept()
    request = client.recv(1024)
    request = str(request)

    if "/approve" in request:
        LED(3).on()
        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nVolgende foto")
        LED(3).off()

    elif "/getphoto" in request:
        img = sensor.snapshot()
        img.rotation_corr(z_rotation=180)
        jpeg = img.compress(quality=50)  # eerst verwerken
        send_code(waarde)
        client.send("HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\n\r\n")
        send_all(client, jpeg)

    elif "/setwaarde?val=" in request:
        try:
            val_str = request.split("val=")[1].split()[0].split("&")[0]
            waarde = int(val_str)

            # Hier kun je de waarde gebruiken, of direct doorsturen

            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nWaarde ontvangen: %d" % waarde)
        except Exception as e:
            print("Fout bij parsen:", e)
            client.send("HTTP/1.1 400 Bad Request\r\n\r\n")

    else:
        LED(3).on()
        LED(2).on()
        LED(1).on()

    client.close()
