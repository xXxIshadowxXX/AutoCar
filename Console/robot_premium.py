import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import time
import cv2
import numpy as np
import threading
from collections import deque
from PIL import ImageDraw

# ----------------------
# Instellingen & Globals
# ----------------------

angle_buffer = deque(maxlen=3)

# IP vragen
try:
    ip_suffix = input("Geef laatste getal van het IP-adres (bijv. 15 voor 192.168.137.15): ").strip()
    ROBOT_IP = f"192.168.137.{ip_suffix}"
except Exception:
    print("❌ Ongeldige invoer. Standaard IP gebruikt.")
    ROBOT_IP = "192.168.137.15"

# ----------------------
# Asynchrone communicatie
# ----------------------

def stuurhoek_naar_robot_async(angle):
    def worker():
        try:
            print(f"Verstuur nu naar robot: {angle}")
            requests.get(f"http://{ROBOT_IP}/setwaarde?val={angle}", timeout=10)
        except:
            pass
    threading.Thread(target=worker, daemon=True).start()

# ----------------------
# Lijnvolg-analyse
# ----------------------

def lijnvolg_analyse(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    y = 120
    row = gray[y, :]
    midden = row.shape[0] // 2
    threshold = np.percentile(row, 20)

    indices = np.where(row < threshold)[0]

    links = indices[indices < midden]
    rechts = indices[indices >= midden]

    left = links.max() if links.size > 0 else 0
    right = rechts.min() if rechts.size > 0 else row.shape[0] - 1

    left_val = row[left]
    right_val = row[right]
    verschil = abs(int(left_val) - int(right_val))

    if verschil > 30:
        if left_val > right_val:
            left = 0
        else:
            right = row.shape[0] - 1

    center = (left + right) // 2
    offset = center - midden
    angle = int((offset + midden) * (90 / (2 * midden)))

    angle_buffer.append(angle)
    gemiddelde_angle = int(sum(angle_buffer) / len(angle_buffer))

    return gemiddelde_angle

# ----------------------
# Bordendetecties (zoals eerder)
# ----------------------

def detect_verplicht_links(img_np):
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img_enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2HSV)
    blue_mask = cv2.inRange(hsv, (90, 30, 30), (150, 255, 255))

    blue_pixels = cv2.countNonZero(blue_mask)
    if blue_pixels < 500:
        return "Geen bord"

    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect = w / float(h)
            if 0.5 < aspect < 2.0:
                roi = img_enhanced[y:y+h, x:x+w]
                roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
                white_mask = cv2.inRange(roi_hsv, (0, 0, 180), (180, 60, 255))
                white_pixels = cv2.countNonZero(white_mask)
                if white_pixels > 300:
                    return "Verplicht links"
    return "Geen bord"

# --- Voor demo houden we nu alleen verplicht links ---
# (Andere borden kunnen later toegevoegd worden in exact dezelfde stijl)

def bord_detectie_worker(img_np):
    result = detect_verplicht_links(img_np)
    if result != "Geen bord":
        print(f"Bord gedetecteerd: {result}")
        label_result.config(text=f"Gevonden bord: {result}")
        return result
    return None

# ----------------------
# Bord handlers
# ----------------------

def board_handler(board_type):
    if board_type == "Verplicht links":
        stuurhoek_naar_robot_async(95)

# ----------------------
# Snelle loop (nu volledig synchroon per frame)
# ----------------------

def snelle_loop():
    try:
        uid = time.time()
        resp = requests.get(f"http://{ROBOT_IP}/getphoto?uid={uid}", timeout=10)
        if "image" in resp.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img_np = np.array(img)

            angle = lijnvolg_analyse(img_np)
            bord_type = bord_detectie_worker(img_np)
            
            if bord_type:
                board_handler(bord_type)
            else:
                stuurhoek_naar_robot_async(angle)

            img_overlay = img.copy()
            draw = ImageDraw.Draw(img_overlay)
            draw.line([(0, 120), (img_overlay.width, 120)], fill=(255, 0, 0), width=2)
            photo = ImageTk.PhotoImage(img_overlay.resize((320, 240)))
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.image = photo

    except Exception as e:
        print("Fout:", e)

    root.after(50, snelle_loop)  # veilige refresh-rate

# ----------------------
# GUI setup
# ----------------------

root = tk.Tk()
root.title("Robot Lijnvolg FAST")

canvas = tk.Canvas(root, width=320, height=240)
canvas.pack()

label_result = tk.Label(root, text="Nog geen foto", font=("Arial", 14))
label_result.pack()

start_button = tk.Button(root, text="Start live", command=snelle_loop)
start_button.pack(pady=10)

root.mainloop()
