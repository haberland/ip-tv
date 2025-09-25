import cv2
import numpy as np
import time

# URL des HDMI-Streams
stream_url = "http://192.168.175.6:8080/hdmi"

# Stream öffnen
cap = cv2.VideoCapture(stream_url)
if not cap.isOpened():
    raise RuntimeError("Stream konnte nicht geöffnet werden!")

# Erstes Snapshot
ret, frame1 = cap.read()
if not ret:
    raise RuntimeError("Konnte erstes Frame nicht lesen")

# Warten, z.B. 1 Sekunde
time.sleep(1)

# Zweites Snapshot
ret, frame2 = cap.read()
if not ret:
    raise RuntimeError("Konnte zweites Frame nicht lesen")

cap.release()

# In Graustufen konvertieren für einfachere Differenz
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

# Differenz berechnen
diff = cv2.absdiff(gray1, gray2)

# Optional: Differenzwert als Summe aller Pixel
diff_sum = np.sum(diff)
print(f"Gesamtdifferenz: {diff_sum}")

# Differenz als Bild speichern
cv2.imwrite("diff.png", diff)

# Bilder speichern, falls benötigt
cv2.imwrite("snapshot1.png", frame1)
cv2.imwrite("snapshot2.png", frame2)
