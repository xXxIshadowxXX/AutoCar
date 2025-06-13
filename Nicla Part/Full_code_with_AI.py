import sensor, image, time
import network, socket
from pyb import LED
from machine import Pin
import ml, math, uos, gc

SSID = "Toondevice"
KEY = "kuijpers"
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

# -- Model setup --
net = None
labels = None
min_confidence = 0.5

try:
    net = ml.Model("trained.tflite", load_to_fb=uos.stat('trained.tflite')[6] > (gc.mem_free() - (64*1024)))
except Exception as e:
    raise Exception('Failed to load "trained.tflite" (' + str(e) + ')')

try:
    labels = [line.rstrip('\n') for line in open("labels.txt")]
except Exception as e:
    raise Exception('Failed to load "labels.txt" (' + str(e) + ')')

colors = [ (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255) ]

threshold_list = [(math.ceil(min_confidence * 255), 255)]

def fomo_post_process(model, inputs, outputs):
    ob, oh, ow, oc = model.output_shape[0]
    x_scale = inputs[0].roi[2] / ow
    y_scale = inputs[0].roi[3] / oh
    scale = min(x_scale, y_scale)
    x_offset = ((inputs[0].roi[2] - (ow * scale)) / 2) + inputs[0].roi[0]
    y_offset = ((inputs[0].roi[3] - (ow * scale)) / 2) + inputs[0].roi[1]
    l = [[] for i in range(oc)]
    for i in range(oc):
        img = image.Image(outputs[0][0, :, :, i] * 255)
        blobs = img.find_blobs(threshold_list, x_stride=1, y_stride=1, area_threshold=1, pixels_threshold=1)
        for b in blobs:
            rect = b.rect()
            x, y, w, h = rect
            score = img.get_statistics(thresholds=threshold_list, roi=rect).l_mean() / 255.0
            x = int((x * scale) + x_offset)
            y = int((y * scale) + y_offset)
            w = int(w * scale)
            h = int(h * scale)
            l[i].append((x, y, w, h, score))
    return l

label_to_value = {
    "Verkeersbord_50": 97,
    "Verkeersbord_Stop": 98,
    "Stoplicht_Groen": 125,
    "Stoplicht_Oranje": 126,
    "Stoplicht_Rood": 127
}

cooldowns = {label: 0 for label in label_to_value.keys()}

FRAMES_DETECTION_TIMES = 5
MIN_DETECTIONS_REQUIRED = 2
recent_detections = []
current_value = 0


def send_all(client, data):
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)
    while data:
        sent = client.send(data)
        data = data[sent:]

def send_code(code):
    global current_value
    current_value = code
    to_zumo.value(1)
    time.sleep_ms(10)
    for i in range(8):
        time.sleep_ms(10)
        to_zumo.value((code >> i) & 1)
    to_zumo.value(0)

waarde = 45

while True:
    client, addr = s.accept()
    req = client.recv(256)
    req = str(req)

    if "/getphoto" in req:
        img = sensor.snapshot().rotation_corr(z_rotation=180)
        jpeg = img.compress(quality=50)
        client.send("HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\n\r\n")
        send_all(client, jpeg)

    elif "/setwaarde?val=" in req:
        try:
            val = int(req.split("val=")[1].split()[0].split("&")[0])
            waarde = val
            send_code(waarde)
            waarde = 92
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nWaarde ontvangen: %d" % val)
            print(val)
        except:
            client.send("HTTP/1.1 400 Bad Request\r\n\r\n")

    elif "/approve" in req:
        LED(3).on()
        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")
        LED(3).off()

    elif "/runai" in req:
        print("AI processing started...")
        img = sensor.snapshot().rotation_corr(z_rotation=180)
        detected_labels = []

        for i, detection_list in enumerate(net.predict([img], callback=fomo_post_process)):
            if i == 0: continue
            if len(detection_list) == 0: continue
            for x, y, w, h, score in detection_list:
                if score < 0.80:
                    continue
                label = labels[i]
                detected_labels.append(label)

        recent_detections.append(detected_labels)
        if len(recent_detections) > FRAMES_DETECTION_TIMES:
            recent_detections.pop(0)

        label_frequency = {}
        for frame_labels in recent_detections:
            for label in frame_labels:
                if label not in label_frequency:
                    label_frequency[label] = 0
                label_frequency[label] += 1

        for label, count in label_frequency.items():
            if label in label_to_value and count >= MIN_DETECTIONS_REQUIRED:
                now = time.time()
                waarde = label_to_value[label]
                if waarde > 90:
                    if waarde != val and now >= cooldowns[label]:
                        waarde = label_to_value[label]
                        send_code(waarde)
                        print("Bevestigde detectie van:", label, "-> waarde:", waarde)
                        cooldowns[label] = now + 5
                    elif waarde != val and now < cooldowns[label]:
                        waarde = 92
                        send_code(waarde)
                        print("In cooldown, tijdelijke waarde 92 gestuurd.")
                else:
                    if now >= cooldowns[label]:
                        waarde = label_to_value[label]
                        send_code(waarde)
                        print("Bevestigde detectie van:", label, "-> waarde:", waarde)
                        cooldowns[label] = now + 5


        print("AI processing done.")
        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")

    client.close()
