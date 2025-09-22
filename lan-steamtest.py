#! /usr/bin/python3
import cv2 #wird zum Bildvergleich verwendet
import time

url = "http://192.168.175.6:8080/hdmi" #Steam URL
schwellenwert = 1000000 # Passen diesen Wert an die Bedürfnisse an, niedrieger Wert höhere Erkennung.

while True:
    try:
        # Öffne den Stream für den ersten Frame
        print("Öffne den Stream für den ersten Frame...")
        cap1 = cv2.VideoCapture(url)
        if not cap1.isOpened():
            print("Konnte den Stream nicht öffnen. Warte 10 Sekunden und versuche es erneut.")
            time.sleep(10)
            continue

        ts1 = int(time.time())
        ret1, frame1 = cap1.read()
        cap1.release()

        if not ret1:
            print("Konnte keinen Frame lesen. Stream ist möglicherweise leer.")
            time.sleep(10)
            continue

        print("Erster Frame gelesen. Warte 10 Sekunden bis zum nächsten Vergleich...")
        time.sleep(10)

        # Öffne den Stream für den zweiten Frame
        print("Öffne den Stream für den zweiten Frame...")
        cap2 = cv2.VideoCapture(url)
        if not cap2.isOpened():
            print("Konnte den Stream nicht öffnen. Warte 10 Sekunden und versuche es erneut.")
            time.sleep(10)
            continue

        ts2 = int(time.time())
        ret2, frame2 = cap2.read()
        cap2.release()
        
        if not ret2:
            print("Konnte keinen Frame lesen. Stream ist möglicherweise leer.")
            time.sleep(10)
            continue

        # Konvertiere Frames und berechne das Delta
        gray_frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        diff = cv2.absdiff(gray_frame1, gray_frame2)
        delta = diff.sum()
        
        if delta > schwellenwert:
            print(f"✅ Bild hat sich geändert! Delta-Wert: {delta}")
        else:
            print(f"❌ Bild hat sich NICHT geändert. Delta-Wert: {delta}")
            print("Der Stream ist möglicherweise eingefroren. Speichere Screenshots...")
            
            dateiname1 = f"eingefroren_bildschirm_1_{delta}_{ts1}.jpg"
            cv2.imwrite(dateiname1, frame1)
            print(f"    - Erster Screenshot gespeichert als: {dateiname1}")
            
            dateiname2 = f"eingefroren_bildschirm_2_{delta}_{ts2}.jpg"
            cv2.imwrite(dateiname2, frame2)
            print(f"    - Zweiter Screenshot gespeichert als: {dateiname2}")

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        time.sleep(30)

print("Programm beendet.")
