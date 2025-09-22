import cv2
import time
import numpy as np
import csv
from datetime import datetime

# Einstellungen
video_device = "/dev/video48"
brightness_threshold = 10
num_measurements = 10
pause_between_measurements = 30  # Sekunden
output_csv = "startup_times.csv"


def send_key(keycode: str, host: str = "127.0.0.1", port: int = 8181):
    url = f"http://{host}:{port}/"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    data = {
        "keycode": keycode,
        "hidden": "on"
    }
    try:
        r = requests.post(url, headers=headers, data=data, timeout=3)
        r.raise_for_status()
        print(f"Key {keycode} erfolgreich gesendet.")
    except requests.RequestException as e:
        print(f"Fehler beim Senden von Key {keycode}: {e}")

# CSV vorbereiten
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Measurement", "Timestamp", "StartupTime_s", "MeanBrightness"])

# Messungen
startup_times = []

for i in range(num_measurements):
    print(f"\n--- Messung {i+1} ---")
    start_time = time.time()
    time.sleep(5)
    send_key("3")
    print("STB eingeschaltet, warte auf Stream...")

    cap = cv2.VideoCapture(video_device)

    while True:
        ret, frame = cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            if mean_brightness > brightness_threshold:
                break
        time.sleep(0.1)

    end_time = time.time()
    startup_time = end_time - start_time
    startup_times.append(startup_time)

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Messung {i+1}: Stream verfügbar nach {startup_time:.2f} Sekunden (mittlere Helligkeit: {mean_brightness:.2f})")

    # in CSV schreiben
    with open(output_csv, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([i+1, timestamp_str, f"{startup_time:.2f}", f"{mean_brightness:.2f}"])

    send_key("3")
    cap.release()
    time.sleep(pause_between_measurements)  # kurze Pause zwischen den Messungen
