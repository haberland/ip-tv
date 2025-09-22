#! /usr/bin/python
import cv2
import time
import numpy as np
import subprocess
import requests
from datetime import datetime

# --- Einstellungen ---
attenuator_ip = "192.168.1.101"
fakercu_ip = "192.168.175.19"

start_db = 48.0
stop_db = 60.0
step_db = 0.25

settle_time = 30          # Sekunden warten nach neuer Dämpfung
snapshot_interval = 1     # Sekunden zwischen Snapshots
threshold = 250000        # Schwellenwert für Diff

# Log-Bild skalieren um größes zu verkeinern
scale = 0.5  # 50 % der Originalgröße

snapshots = []
greyshots = []
timestamps = []

def send_key(keycode: str, host: str = "0.0.0.0", port: int = 8181):
    url = f"http://{fakercu_ip}:{port}/"
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

print("[Setup] Wecke Stream...")
# --- Dämpfung einstellen ---
cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{start_db}"]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"[Setup] Dämpfung gesetzt: {start_db} dB")
time.sleep(5)
send_key("25")
print(f"[Setup] 4 Sekunden warten...")
time.sleep(5)
send_key("27")

# Grabber öffnen
cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("[Error] Grabber konnte nicht geöffnet werden!")
    exit(1)

print("[Setup] Starte Stream-Überwachung...")
snapshots.clear()
for i in range(3):
    time.sleep(snapshot_interval)
    ret, frame = cap.read()
    if not ret:
        print("[Error] Kein Frame gelesen → Stream tot.")
        cap.release()
        exit(1)
    snapshots.append(frame)

    filename = f"{i} Snapshot.jpg"
    cv2.imwrite(filename, snapshots[i])
    snapshots.append(frame)

damping = start_db
while damping <= stop_db:
    # --- Dämpfung einstellen ---
    cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{damping:.2f}"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[Testing] Dämpfung gesetzt: {damping:.2f} dB")

    # --- Wartezeit nach Dämpfungsänderung ---
    time.sleep(settle_time)

    snapshots.clear()
    greyshots.clear()
    timestamps.clear()

    # 3 Snapshots sammeln
    for i in range(3):
        time.sleep(snapshot_interval)
        timestamp = datetime.now().strftime("%d.%m.%Y %H%M%S")
        ret, frame = cap.read()
        if not ret:
            print("[Error] Kein Frame gelesen → Stream tot.")
            cap.release()
            exit(1)
        
        snapshots.append(frame)
        timestamps.append(timestamp)
        filename = f"{i} Snapshot.jpg"
        cv2.imwrite(filename, snapshots[i])
        greyshot = cv2.cvtColor(snapshots[i], cv2.COLOR_BGR2GRAY)
        filename = f"{i} grey Snapshot.jpg"
        greyshots.append(greyshot)
        cv2.imwrite(filename, greyshots[i])
        print(f"[Testing] Snapshot {i+1} aufgenommen")

    # Differenzen berechnen
    diffs = []
    diff_values = []
    for i in range(2):
        diff = cv2.absdiff(greyshots[i], greyshots[i+1])
        filename = f"{i} grey Diff.jpg"
        cv2.imwrite(filename, diff)
        diffs.append(diff)
        diff_value = np.sum(diff)
        diff_values.append(diff_value)
        print(f"[Testing] Diff {i+1}: {diff_value}")

    # Prüfen ob Stream hängt / alle kleiner Schwellwert
    #if all(d < threshold for d in diffs):
    # Prüfen ob Stream hängt / einer kleiner Schwellwert
    if any(d < threshold for d in diff_values):
        for idx, snap in enumerate(snapshots):
            filename = f"snapshot_{idx}.jpg"
            cv2.imwrite(filename, snap)
            print(f"[Result] Snapshot gespeichert: {filename}")
        print("[Result] Stream hängt → Daten werden gesichert.")

        for i in range(3):
            filename = f"{timestamps[i]}_{damping}_Snapshot_{i}.jpg"
            smaller = cv2.resize(snapshots[i], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            cv2.imwrite(filename, smaller)
        for i in range(2):
            filename = f"{timestamps[i]}_{damping}_{diff_values[i]}_Diff_{i}.jpg"
            smaller = cv2.resize(diffs[i], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            cv2.imwrite(filename, smaller)
        break

    # --- nächste Dämpfung ---
    send_key("26")
    time.sleep(3)
    send_key("24")
    damping += step_db

cap.release()
print(f"+-------------------------------+")
print(f"| Messung beendet, Stream hängt |")
print(f"+-------------------------------+")
print(f"{timestamps[0]}, Dämpfung: {damping}, Diff: {diff_value}")
print(f"")

with open("Messung.txt", "a") as f:
    print(f"{timestamps[0]},{start_db},{stop_db},{step_db},{settle_time},{snapshot_interval},{threshold},{damping},{diff_value}", file=f)

cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{start_db}"]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"Dämpfung gesetzt: {start_db} dB")
time.sleep(5)
send_key("25")
time.sleep(5)
send_key("27")
print("[Goodbye] Messung beendet → Programm beendet.")
exit(0)
