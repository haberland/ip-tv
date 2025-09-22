#! /usr/bin/python
import os
import cv2
import csv
import time
import numpy as np
from datetime import datetime

video_device = "/dev/video48"
snapshot_interval = 1     # Sekunden zwischen Snapshots
threshold = 250000        # Schwellenwert für Differenz

# Log-Bild skalieren um größes zu verkeinern
scale = 0.5  # 50 % der Originalgröße

snapshots = []
greyshots = []
timestamps = []

timestamp_test = datetime.now().strftime("%Y%m%d-%H%M%S")
ordner_name = f"{timestamp_test}_Messung"
os.makedirs(ordner_name, exist_ok=True)

csv_datei = os.path.join(ordner_name, "messung.csv")

def speichere_messung(timestamp, snapshot_interval, threshold, diff_value):
    # Header festlegen
    header = ["timestamp", "snapshot interval", "threshold", "diff value"]
    # Messwerte
    daten = [timestamp, snapshot_interval, threshold, diff_value]
    # Prüfen, ob Datei existiert
    datei_existiert = os.path.exists(csv_datei)
    # Datei öffnen (append = "a")
    with open(csv_datei, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Falls neu → zuerst Header schreiben
        if not datei_existiert:
            writer.writerow(header)
        # Datenzeile anhängen
        writer.writerow(daten)
    #print(f"Messung gespeichert: {daten}")

# Grabber öffnen
cap = cv2.VideoCapture(video_device, cv2.CAP_V4L2)
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
    filename = f"live Snapshot {i}.jpg"
    filename = os.path.join(ordner_name, filename)
    cv2.imwrite(filename, snapshots[i])
    snapshots.append(frame)

    filename = f"live Snapshot grey {i}.jpg"
    filename = os.path.join(ordner_name, filename)
    cv2.imwrite(filename, snapshots[i])

while True:
    snapshots.clear()
    greyshots.clear()
    timestamps.clear()

    # 3 Snapshots sammeln
    for i in range(3):
        time.sleep(snapshot_interval)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        timestamp_file = datetime.now().strftime("%Y%m%d-%H%M%S")
        ret, frame = cap.read()
        if not ret:
            print("[Error] Kein Frame gelesen → Stream tot.")
            cap.release()
            exit(1)
        
        snapshots.append(frame)
        timestamps.append(timestamp)
        filename = f"live Snapshot {i}.jpg"
        filename = os.path.join(ordner_name, filename)
        cv2.imwrite(filename, snapshots[i])
        greyshot = cv2.cvtColor(snapshots[i], cv2.COLOR_BGR2GRAY)
        greyshots.append(greyshot)
        filename = f"live Snapshot grey {i}.jpg"
        filename = os.path.join(ordner_name, filename)
        cv2.imwrite(filename, greyshots[i])
        print(f"[Testing] Snapshot {i+1} aufgenommen")

    # Differenzen berechnen
    diffs = []
    diff_values = []
    for i in range(2):
        diff = cv2.absdiff(greyshots[i], greyshots[i+1])
        diffs.append(diff)
        diff_value = np.sum(diff)
        diff_values.append(diff_value)
        filename = f"live Snapshot grey Diff {i}.jpg"
        filename = os.path.join(ordner_name, filename)
        cv2.imwrite(filename, diff)
        print(f"[Testing] Diff {i+1}: {diff_value}")

    speichere_messung(timestamp=timestamps[0] ,snapshot_interval=snapshot_interval, threshold=threshold, diff_value=diff_value)

    # Prüfen ob Stream hängt / alle kleiner Schwellwert
    #if all(d < threshold for d in diffs):
    # Prüfen ob Stream hängt / einer kleiner Schwellwert
    if any(d < threshold for d in diff_values):
        print("[Result] Stream hängt → Daten werden gesichert.")
        for idx, snap in enumerate(snapshots):
            filename = f"{timestamp_file}_Snapshot_{idx}.jpg"
            smaller = cv2.resize(snapshots[idx], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            filename = os.path.join(ordner_name, filename)
            cv2.imwrite(filename, smaller)
        print("[Result] Stream hängt → Daten werden gesichert.")
        for idx, snap in enumerate(greyshots):
            filename = f"{timestamp_file}_Snapshot_grey_{idx}.jpg"
            smaller = cv2.resize(greyshots[idx], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            filename = os.path.join(ordner_name, filename)
            cv2.imwrite(filename, smaller)
        print("[Result] Sichere Differenzdaten...")
        for idx, snap in enumerate(diffs):
            filename = f"{timestamp_file}_{diff_values[i]}_Diff_{i}.jpg"
            smaller = cv2.resize(diffs[i], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            filename = os.path.join(ordner_name, filename)
            cv2.imwrite(filename, smaller)
        break

cap.release()
print(f"+-------------------------------+")
print(f"| Messung beendet, Stream hängt |")
print(f"+-------------------------------+")
print(f"{timestamps[0]}, Diff: {diff_value}")
print(f"")

print("[Goodbye] Messung beendet → Programm beendet.")
exit(0)
