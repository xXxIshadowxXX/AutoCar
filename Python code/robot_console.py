import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import time
import cv2
import numpy as np

ROBOT_IP = "192.168.137.180"  # Zet hier jouw Nicla IP

def download_and_process():
    try:
        # Capture en download afbeelding
        requests.get(f"http://{ROBOT_IP}/capture", timeout=5)
        time.sleep(0.5)
        uid = time.time()
        resp = requests.get(f"http://{ROBOT_IP}/getphoto?uid={uid}", timeout=5)

        if "image" in resp.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img_np = np.array(img)

            # Detectie
            result_text = detect_stop_sign(img_np)

            # Toon afbeelding
            photo = ImageTk.PhotoImage(img.resize((320, 240)))
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.image = photo
            label_result.config(text=f"Herkenning: {result_text}")

            # Als herkend, stuur signaal
            if result_text != "Geen bord":
                requests.get(f"http://{ROBOT_IP}/approve", timeout=2)

    except Exception as e:
        label_result.config(text=f"Fout: {e}")

    # Herhaal elke 2 sec
    root.after(2000, download_and_process)

def detect_stop_sign(img_np):
    # Dummy detectie: zoek veel rood in het beeld
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    lower_red = (0, 70, 50)
    upper_red = (10, 255, 255)
    mask = cv2.inRange(hsv, lower_red, upper_red)

    if np.sum(mask) > 50000:
        return "STOP-bord"
    return "Geen bord"

# GUI setup
root = tk.Tk()
root.title("Robot verkeersbord herkenning")

canvas = tk.Canvas(root, width=320, height=240)
canvas.pack()

label_result = tk.Label(root, text="Nog geen foto", font=("Arial", 14))
label_result.pack()

start_button = tk.Button(root, text="Start live", command=download_and_process)
start_button.pack(pady=10)

root.mainloop()
