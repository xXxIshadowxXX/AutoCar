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

            img_overlay = img.copy()
            draw = ImageDraw.Draw(img_overlay)
            draw.line([(0, 120), (img_overlay.width, 120)], fill=(255, 0, 0), width=2)
            photo = ImageTk.PhotoImage(img_overlay.resize((320, 240)))
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.image = photo

    except Exception as e:
        print("Fout:", e)

    root.after(30, snelle_loop)  # +/- 30 FPS

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
