import subprocess
import csv
import time
from datetime import datetime

def log_memory_usage(device_ip: str, csv_file: str = "memory_usage.csv"):
    """
    Liest den aktuellen Speicherverbrauch der STB über ADB aus
    und speichert die Werte mit Zeitstempel in eine CSV-Datei.

    :param device_ip: IP der STB, z.B. "192.168.175.106"
    :param csv_file: Pfad zur CSV-Datei
    """
    # Verbindung aufbauen (falls noch nicht verbunden)
    subprocess.run(["adb", "connect", device_ip], check=True)

    # Speicherwerte abrufen
    result = subprocess.run(
        ["adb", "-s", device_ip, "shell", "free", "-m"],
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )

    lines = result.stdout.strip().splitlines()
    if len(lines) < 2:
        print("Fehler: unerwartete Ausgabe von free -m")
        return

    header = lines[0].split()  # z.B. ["total", "used", "free", "shared", "buff/cache", "available"]
    values = lines[1].split()

    if values[0].lower().startswith("mem"):
        values = values[1:]

    # Zeitstempel hinzufügen
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp] + values
    header_row = ["timestamp"] + header

    # CSV schreiben / anhängen
    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        if f.tell() == 0:  # Header nur schreiben, wenn Datei leer
            writer.writerow(header_row)
        writer.writerow(row)

    print(f"✅ Speicherwerte geloggt: {row}")



device_ip = "192.168.175.106"

for i in range(5):  # 5 Messungen
    log_memory_usage(device_ip)
    time.sleep(10)  # 10 Sekunden warten