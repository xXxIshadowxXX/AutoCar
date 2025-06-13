import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import requests
from io import BytesIO
import time
import cv2
import numpy as np
import threading
from collections import deque, defaultdict

# ---------------------- Instellingen ----------------------

angle_buffer = deque(maxlen=3)
bord_detectie_counter = defaultdict(lambda: {"count": 0, "cooldown": 0})

# IP vragen
try:
    ip_suffix = input("Geef laatste getal van het IP-adres (bijv. 15 voor 192.168.137.15): ").strip()
    ROBOT_IP = f"192.168.125.{ip_suffix}"
except Exception:
    ROBOT_IP = "192.168.137.15"

# ------------------ Communicatie ------------------

def stuurhoek_naar_robot_async(angle):
    def worker():
        try:
            print(f"Verstuur nu naar robot: {angle}")
            requests.get(f"http://{ROBOT_IP}/setwaarde?val={angle}", timeout=10)
        except:
            pass
    threading.Thread(target=worker, daemon=True).start()

# ------------------ Lijnvolg-analyse ------------------

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

# ------------------ Bordendetecties ------------------

def detect_verplicht_links(img_np):
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img_enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2HSV)
    blue_mask = cv2.inRange(hsv, (100, 50, 50), (130, 255, 255))

    blue_pixels = cv2.countNonZero(blue_mask)
    if blue_pixels < 500:
        return "Geen bord"

    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 2000:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h)
        if aspect < 1.2:
            continue

        roi = img_enhanced[y:y+h, x:x+w]
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
        white_mask = cv2.inRange(roi_hsv, (0, 0, 180), (180, 60, 255))
        white_pixels = cv2.countNonZero(white_mask)

        if white_pixels > 500:
            return "Verplicht links"

    return "Geen bord"
  
def detect_haaientand(img_np):
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img_enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2HSV)
    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 70, 50), (180, 255, 255))
    red_mask = cv2.bitwise_or(mask1, mask2)

    red_pixels = cv2.countNonZero(red_mask)
    if red_pixels < 500:
        return "Geen bord"

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
        if len(approx) >= 3:
            x, y, w, h = cv2.boundingRect(approx)
            aspect = w / float(h)
            if 0.5 < aspect < 2.0:
                roi = img_enhanced[y:y+h, x:x+w]
                roi_hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
                white_mask = cv2.inRange(roi_hsv, (0, 0, 180), (180, 60, 255))
                white_pixels = cv2.countNonZero(white_mask)
                if white_pixels > 300:
                    return "Haaientand-bord"
    return "Geen bord"

def detect_voorrangsbord(img_np):
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img_enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2HSV)
    yellow_mask = cv2.inRange(hsv, (20, 100, 100), (35, 255, 255))

    yellow_pixels = cv2.countNonZero(yellow_mask)
    if yellow_pixels < 300:
        return "Geen bord"

    contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 800:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)

        if len(approx) == 4:
            _, (rw, rh), angle = cv2.minAreaRect(cnt)
            ratio = rw / rh if rh != 0 else 0
            if 0.6 < ratio < 1.4:
                return "Voorrangsbord"

    return "Geen bord"

# ------------------ Debounce logica ------------------

def check_and_handle_bord(bordnaam):
    now = time.time()
    data = bord_detectie_counter[bordnaam]

    if data["cooldown"] > now:
        return False

    if 'last_seen' in data and (now - data['last_seen']) > 3:
        data["count"] = 0

    data["count"] += 1
    data["last_seen"] = now

    print(f"{bordnaam} gedetecteerd: {data['count']}/3")

    if data["count"] >= 3:
        data["count"] = 0
        data["cooldown"] = now + 10
        return True

    return False

# ------------------ Borddetectie worker ------------------

def bord_detectie_worker(img_np):
    detecties = [
        (detect_verplicht_links, "Verplicht links"),
        (detect_haaientand, "Haaientand-bord"),
        (detect_voorrangsbord, "Voorrangsbord"),
    ]

    barrier = threading.Barrier(len(detecties) + 1)
    result_container = [None]

    def detect_and_handle(detect_func, bordnaam):
        result = detect_func(img_np)
        if result != "Geen bord" and result_container[0] is None:
            if check_and_handle_bord(result):
                print(f"{bordnaam} bevestigd na debounce!")
                result_container[0] = result
        barrier.wait()

    for detect_func, bordnaam in detecties:
        threading.Thread(target=detect_and_handle, args=(detect_func, bordnaam), daemon=True).start()

    barrier.wait()
    return result_container[0]

# ------------------ Bord handler ------------------

def board_handler(board_type):
    if board_type == "Verplicht links":
        waarde = 95
    elif board_type == "Haaientand-bord":
        waarde = 96
    elif board_type == "Voorrangsbord":
        waarde = 93
    else:
        return

    # 3x sturen met korte vertraging
    for _ in range(3):
        stuurhoek_naar_robot_async(waarde)
        time.sleep(0.1)  # 100 ms pauze tussen verzendingen


# -----------------Run ai worker--------------------
# Extra bovenaan plaatsen:
runai_lock = threading.Lock()

def runai_worker():
    with runai_lock:
        try:
            requests.get(f"http://{ROBOT_IP}/runai", timeout=10)
        except Exception as e:
            print("Fout in runai_worker:", e)


# ------------------ Snelle loop ------------------

def snelle_loop():
    try:
        uid = time.time()
        resp = requests.get(f"http://{ROBOT_IP}/getphoto?uid={uid}", timeout=10)
        if "image" not in resp.headers.get("Content-Type", ""):
            print("Geen geldige foto ontvangen, probeer opnieuw...")
            root.after(500, snelle_loop)
            return

        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img_np = np.array(img)

        # Eerst: optioneel runai uitvoeren
        if runai_enabled.get():
            try:
                requests.get(f"http://{ROBOT_IP}/runai", timeout=10)
            except Exception as e:
                print("Fout bij runai:", e)

        # Daarna gewoon verder met de normale verwerking
        barrier = threading.Barrier(3)
        result_container = {"angle": None, "bord": None}

        def lijnvolg_worker():
            angle = lijnvolg_analyse(img_np)
            result_container["angle"] = angle
            barrier.wait()

        def bord_worker():
            bord = bord_detectie_worker(img_np)
            result_container["bord"] = bord
            barrier.wait()

        threading.Thread(target=lijnvolg_worker, daemon=True).start()
        threading.Thread(target=bord_worker, daemon=True).start()
        barrier.wait()

        if result_container["bord"]:
            board_handler(result_container["bord"])
            label_result.config(text=f"Gevonden bord: {result_container['bord']}")
        else:
            stuurhoek_naar_robot_async(result_container["angle"])
            label_result.config(text="Geen bord")

        img_overlay = img.copy()
        draw = ImageDraw.Draw(img_overlay)
        draw.line([(0, 120), (img_overlay.width, 120)], fill=(255, 0, 0), width=2)
        photo = ImageTk.PhotoImage(img_overlay.resize((320, 240)))
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo

    except Exception as e:
        print("Fout:", e)
        root.after(500, snelle_loop)
        return

    root.after(25, snelle_loop)

# ------------------ GUI ------------------

root = tk.Tk()
root.title("Robot Lijnvolg PREMIUM")

canvas = tk.Canvas(root, width=320, height=240)
canvas.pack()

label_result = tk.Label(root, text="Nog geen foto", font=("Arial", 14))
label_result.pack()

runai_enabled = tk.BooleanVar(value=True)
runai_checkbox = tk.Checkbutton(root, text="Gebruik runai", variable=runai_enabled)
runai_checkbox.pack()

start_button = tk.Button(root, text="Start live", command=snelle_loop)
start_button.pack(pady=10)

root.mainloop()
