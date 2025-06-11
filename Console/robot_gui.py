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

lijn_lock = threading.Lock()
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
            requests.get(f"http://{ROBOT_IP}/setwaarde?val={angle}", timeout=5)
        except:
            pass
    threading.Thread(target=worker, daemon=True).start()

# ----------------------
# Lijnvolg-analyse
# ----------------------

def lijnvolg_analyse_thread(img_np):
    if not lijn_lock.acquire(blocking=False):
        return

    try:
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

        # Grijswaarden check (vertrouwenslogica)
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

        print(f"Left: {left} ({left_val}), Right: {right} ({right_val}), Offset: {offset} → Stuurhoek: {gemiddelde_angle}")

        stuurhoek_naar_robot_async(gemiddelde_angle)

    except Exception as e:
        print(f"Lijnanalyse fout: {e}")
    finally:
        lijn_lock.release()

# ----------------------
# Bordendetectie
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

def detect_voorrangsbord(img_np):
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    yellow_mask = cv2.inRange(hsv, (20, 100, 100), (35, 255, 255))

    yellow_pixels = cv2.countNonZero(yellow_mask)
    if yellow_pixels < 500:
        return "Geen bord"

    contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 300:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)

        if len(approx) == 4:
            _, (rw, rh), angle = cv2.minAreaRect(cnt)
            if 30 < abs(angle) < 60:
                return "Voorrangsbord"

    return "Geen bord"

def detect_verboden_toegang(img_np):
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 70, 50), (180, 255, 255))
    red_mask = cv2.bitwise_or(mask1, mask2)

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 500:
            continue

        (x, y), radius = cv2.minEnclosingCircle(cnt)
        circle_area = np.pi * (radius ** 2)
        roundness = area / circle_area
        if roundness < 0.6:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        pad = 10
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_np.shape[1] - x, w + 2*pad)
        h = min(img_np.shape[0] - y, h + 2*pad)
        roi = img_np[y:y+h, x:x+w]

        lab = cv2.cvtColor(roi, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        roi_rgb = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

        roi_hsv = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2HSV)
        white_mask = cv2.inRange(roi_hsv, (0, 0, 200), (180, 30, 255))
        white_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for wc in white_contours:
            wx, wy, ww, wh = cv2.boundingRect(wc)
            aspect = ww / float(wh)
            if aspect > 4 and wh < h * 0.5 and wy > h * 0.3 and wy < h * 0.7:
                return "Verboden toegang"

    return "Geen bord"

def detect_haaientand(img_np):
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 70, 50), (180, 255, 255))
    red_mask = cv2.bitwise_or(mask1, mask2)

    red_pixels = cv2.countNonZero(red_mask)
    if red_pixels < 1000:
        return "Geen bord"

    edges = cv2.Canny(red_mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=20, maxLineGap=10)

    if lines is None or len(lines) < 3:
        return "Geen bord"
    if len(lines) > 10:
        return "Geen bord"

    template = np.zeros_like(red_mask)
    height, width = template.shape
    pts = np.array([[width // 2, height // 4], [width // 4, 3 * height // 4], [3 * width // 4, 3 * height // 4]], np.int32)
    cv2.drawContours(template, [pts], 0, 255, thickness=cv2.FILLED)

    result = cv2.matchTemplate(red_mask, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    if max_val > 0.3:
        return "Haaientand-bord"

    return "Geen bord"

# ----------------------
# Bord handlers
# ----------------------

def board_handler(board_type, stop_time=3):
    print(f"{board_type} detected!")
    # Stop the line-following process for the given time
    stop_line_following(stop_time)

def stop_line_following(seconds):
    global lijn_lock
    print(f"Pausing line-following for {seconds} seconds.")
    lijn_lock.acquire(blocking=True)  # Pauses the line-following thread
    threading.Timer(seconds, lambda: lijn_lock.release()).start()  # Releases after 'seconds'


# ----------------------
# Snelle loop (hogere FPS)
# ----------------------

def snelle_loop():
    uid = time.time()
    try:
        resp = requests.get(f"http://{ROBOT_IP}/getphoto?uid={uid}", timeout=5)
        if "image" in resp.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img_np = np.array(img)

            threading.Thread(target=lijnvolg_analyse_thread, args=(img_np,), daemon=True).start()

            # Trigger board detection
            board_type = detect_verplicht_links(img_np)  # Add additional board types here as needed
            if board_type != "Geen bord":
                board_handler(board_type)  # Handler for the detected board

            # Update the label with the detected board type
            label_result.config(text=f"Gevonden bord: {board_type}")  # Update the label text

            img_overlay = img.copy()
            draw = ImageDraw.Draw(img_overlay)
            draw.line([(0, 120), (img_overlay.width, 120)], fill=(255, 0, 0), width=2)
            photo = ImageTk.PhotoImage(img_overlay.resize((320, 240)))
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.image = photo

    except Exception as e:
        print("Fout:", e)

    root.after(1, snelle_loop)  # 

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
