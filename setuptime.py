import cv2
import time
import numpy as np

# Startzeitpunkt setzen
start_time = time.time()
print("STB eingeschaltet, warte auf Stream...")

# Grabber öffnen
cap = cv2.VideoCapture("/dev/video48")

# Warten, bis der Stream ankommt (nur Frames mit Helligkeit > threshold)
brightness_threshold = 10  # experimentell anpassen
while True:
    ret, frame = cap.read()
    if ret:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        if mean_brightness > brightness_threshold:
            break
    time.sleep(0.1)  # 100ms warten, CPU schonen

# Endzeitpunkt setzen
end_time = time.time()
startup_time = end_time - start_time

print(f"Stream verfügbar nach {startup_time:.2f} Sekunden (mittlere Helligkeit: {mean_brightness:.2f})")

cap.release()
