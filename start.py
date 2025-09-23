from pathlib import Path
import json
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import html
import time
import csv
from datetime import datetime
from typing import Optional, Dict, List
import cv2
import time
import numpy as np
import subprocess
import requests
from datetime import datetime

output_csv = "Testmessung.csv"

config_file = "config.json"
softversion = "1.20.624"

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

def get_or_create_data(filename=config_file):
    file_path = Path(filename)

    if file_path.exists():
        print(f"📂 Eine {filename} wurde gefunden – Daten werden geladen...")
        with open(file_path, "r") as f:
            data = json.load(f)

        print("\nGeladene Daten :")
        for key, value in data.items():
            print(f"{key}: {value}")

        choice = input("\nSind diese Daten korrekt? (j/n): ").strip().lower()
        if choice == "j":
            return data
        else:
            print("⚠️ Daten werden überschrieben...")
            return ask_and_save(file_path)
    else:
        print(f"⚠️ {filename} nicht gefunden – bitte Werte eingeben:")
        return ask_and_save(file_path)


def ask_and_save(file_path: Path):
    """Hilfsfunktion für die Eingaben und das Speichern"""

    choice = input("\nIst die Fritz!Box Gateway und Accesspoint in einem Gerät? (j/n): ").strip().lower()
    if choice == "j":
        fritzbox1 = input("Bitte gib die IP der Fritz!Box ein: ")
        fritzbox2 = fritzbox1
        fritzbox1pass = input("Bitte gib das Passwort der Fritz!Box ein: ")
        fritzbox2pass = fritzbox1pass
    else:
        fritzbox1 = input("Bitte gib die IP der Gateway Fritz!Box ein: ")
        fritzbox1pass = input("Bitte gib das Passwort der Gateway Fritz!Box ein: ")
        fritzbox2 = input("Bitte gib die IP der Wlan-Accesspoint Fritz!Box ein: ")
        fritzbox2pass = input("Bitte gib das Passwort der Wlan-Accesspoint Fritz!Box ein: ")
    attenuator_ip = input("Bitte gib die IP des Dämpfungsgliedes ein: ")
    inputt = input("Bitte gib die IP der FakeRCU ein: ")
    fakercu_ip, port = inputt.split(":")
    if not port.strip():  # leer?
        fakercu_port = int(80)
    else:
        fakercu_port = int(port)
        
    start_db = float(input("Bitte gib Startdämpfung ein (0-90dB): ").replace(",", "."))
    stop_db = float(input("Bitte gib Enddämpfung ein (0-90dB): ").replace(",", "."))
    step_db = float(input("Bitte gib Dämpfungsschrittgröße ein (0,25-95,0dB): ").replace(",", "."))

    settle_time = int(input("Bitte gib die Wartezeit nach der Dämpfung in Sekunden ein: "))
    snapshot_interval = float(input("Bitte gib die Wartezeit zwischen den Snapshots in Sekunden ein (z.B. 1,5): "))
    threshold = int(input("Bitte gib den Schwellwert für die Differenz zwischen den Snapshots an (typisch 250000): "))

    # Log-Bild skalieren um größes zu verkeinern
    inputt = int(input("Bitte gib die Bildgröße in Prozent für das Log ein (1-100): "))
    scale = inputt /100
    videodevice = input("Bitte gib den Pfad des Video-Grabbers an (z. B. /dev/video0): ")

    duration = int(abs(stop_db - start_db) / step_db * (settle_time + 3 * snapshot_interval) / 60)
    loops = int(input(f"Bitte gib die Testanzahl an (1 Testlauf dauert ca. {duration} Minuten): "))

    lastupdate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "Version": "1.20.625",
        "fritzbox1": fritzbox1,
        "fritzbox1pass": fritzbox1pass,
        "fritzbox2": fritzbox2,
        "fritzbox2pass": fritzbox2pass,
        "attenuator_ip": attenuator_ip,
        "fakercu_ip": fakercu_ip,
        "fakercu_port": fakercu_port,

        "start_db": start_db,
        "stop_db": stop_db,
        "step_db": step_db,

        "settle_time": settle_time,
        "snapshot_interval": snapshot_interval,
        "threshold": threshold,

        "scale": scale,
        "videodevice": videodevice,
        "loops": loops,
        "lastupdate": lastupdate
    }

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Daten wurden in {file_path} gespeichert")
    return data

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def _find_tag_text(xml: str, localname: str) -> Optional[str]:
    """Namespace-agnostisch nach <...LocalName> suchen und Text zurückgeben."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    for el in root.iter():
        if el.tag and el.tag.endswith(localname):
            return (el.text or "").strip()
    return None


def _extract_inner_userlist(response_text: str) -> Optional[str]:
    """Extrahiert den UserList-Teil aus der SOAP-Antwort und gibt das XML zurück."""
    if "<NewX_AVM-DE_UserList>" not in response_text:
        return None
    start = response_text.find("<NewX_AVM-DE_UserList>") + len("<NewX_AVM-DE_UserList>")
    end = response_text.find("</NewX_AVM-DE_UserList>")
    inner = response_text[start:end]
    return html.unescape(inner)


# -----------------------------
# FritzBox-Client
# -----------------------------
class FritzTR064:
    def __init__(self, ip: str, password: str, user: Optional[str] = None,
                 port: int = 49000, proto: str = "http"):
        self.ip = ip
        self.user = user
        self.password = password
        self.port = port
        self.proto = proto
        self.base = f"{self.proto}://{self.ip}:{self.port}"

    def _soap_request(self, service: str, location: str, action: str, body: str, timeout: int = 5) -> str:
        url = self.base + location
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{service}#{action}"',
            "User-Agent": "python-TR064-client/1.0"
        }
        resp = requests.post(
            url,
            headers=headers,
            data=body,
            auth=HTTPDigestAuth(self.user, self.password) if self.user else None,
            timeout=timeout,
            verify=False
        )
        resp.raise_for_status()
        return resp.text

    def fetch_username(self) -> Optional[str]:
        """Fragt den ersten Fritzbox-User via X_AVM-DE_GetUserList ab."""
        service = "urn:dslforum-org:service:LANConfigSecurity:1"
        location = "/upnp/control/lanconfigsecurity"
        action = "X_AVM-DE_GetUserList"
        body = """<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
          <s:Body>
            <u:X_AVM-DE_GetUserList xmlns:u="urn:dslforum-org:service:LANConfigSecurity:1"/>
          </s:Body>
        </s:Envelope>"""
        resp = requests.post(
            self.base + location,
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": f"{service}#{action}"
            },
            data=body,
            verify=False,
            timeout=5
        )
        resp.raise_for_status()
        inner = _extract_inner_userlist(resp.text)
        if not inner:
            return None
        try:
            root = ET.fromstring(inner)
            user = root.find(".//Username")
            self.user = user.text if user is not None else None
            return self.user
        except ET.ParseError:
            return None

    def get_total_associations(self, instance: int = 1) -> int:
        service = f"urn:dslforum-org:service:WLANConfiguration:{instance}"
        location = f"/upnp/control/wlanconfig{instance}"
        action = "GetTotalAssociations"
        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <s:Body>
                <u:{action} xmlns:u="{service}"/>
            </s:Body>
        </s:Envelope>"""
        xml = self._soap_request(service, location, action, body)
        val = _find_tag_text(xml, "NewTotalAssociations")
        try:
            return int(val) if val is not None else 0
        except ValueError:
            return 0

    def get_associated_devices(self, wlan_instance: int = 1) -> List[Dict[str, Optional[str]]]:
        """Liefert alle verbundenen Geräte für ein WLAN (2.4 oder 5 GHz)."""
        total = self.get_total_associations(wlan_instance)
        devices = []
        for i in range(total):
            devices.append(self.get_generic_associated_device_info(i, wlan_instance))
        return devices

    def get_generic_associated_device_info(self, index: int, wlan_instance: int = 1) -> Dict[str, Optional[str]]:
        service = f"urn:dslforum-org:service:WLANConfiguration:{wlan_instance}"
        location = f"/upnp/control/wlanconfig{wlan_instance}"
        action = "GetGenericAssociatedDeviceInfo"
        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <s:Body>
                <u:{action} xmlns:u="{service}">
                    <NewAssociatedDeviceIndex>{index}</NewAssociatedDeviceIndex>
                </u:{action}>
            </s:Body>
        </s:Envelope>"""
        xml = self._soap_request(service, location, action, body)
        keys = [
            "NewAssociatedDeviceMACAddress",
            "NewAssociatedDeviceIPAddress",
            "NewAssociatedDeviceAuthState",
            "NewX_AVM-DE_Speed",
            "NewX_AVM-DE_SignalStrength",
            "NewX_AVM-DE_ChannelWidth"
        ]
        return {k: _find_tag_text(xml, k) for k in keys} | {"_raw_xml": xml}



def get_download_speed(fritz: FritzTR064, wan_instance: int = 1, interval: float = 1.0) -> float:
    """
    Liefert die aktuelle Downloadgeschwindigkeit in Bytes/s.
    Interval = Wartezeit zwischen zwei Abfragen, um die Rate zu berechnen.
    """
    service = f"urn:dslforum-org:service:WANCommonInterfaceConfig:{wan_instance}"
    location = f"/upnp/control/wancommonifconfig{wan_instance}"
    action = "GetTotalBytesReceived"

    body = f"""<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
        s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
            <u:{action} xmlns:u="{service}"/>
        </s:Body>
    </s:Envelope>"""

    xml1 = fritz._soap_request(service, location, action, body)
    bytes1 = int(_find_tag_text(xml1, "NewTotalBytesReceived") or 0)
    time.sleep(interval)
    xml2 = fritz._soap_request(service, location, action, body)
    bytes2 = int(_find_tag_text(xml2, "NewTotalBytesReceived") or 0)

    return (bytes2 - bytes1) / interval  # Bytes pro Sekunde


print("Dieses Skript prüft einen HDMI Stream und loggt verbundene WLAN-Geräte der Fritzbox in eine CSV Datei.")
# Beispielaufruf
daten = get_or_create_data(config_file)

print("\n\n✅ Programm startet....")

software = "1.20.625"

if software != daten.get("version"):
    print(f" Dateiversion: {daten.get("version")} != Softwareversion: {software}")
    exit(1)

locals().update(daten)

duration = int(abs(stop_db - start_db) / step_db * (settle_time + 3 * snapshot_interval) / 60) * int(loops) / 60
print(f"Alle Testläufe dauern ca. {duration} Stunden.")








snapshots = []
greyshots = []
timestamps = []



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

timestamp2 = datetime.now().strftime("%Y%m%d-%H%M%S")

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



box1 = FritzTR064(fritzbox2, fritzbox2pass)
box2 = FritzTR064(fritzbox1, fritzbox1pass)

box1.fetch_username()
box2.fetch_username()

# CSV vorbereiten
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "NewAssociatedDeviceMACAddress", "NewAssociatedDeviceIPAddress", "Band", "NewAssociatedDeviceAuthState", "AVM-DE_SignalStrength", "AVM-DE_Speed", "DownloadSpeed_kBps"])

for loop in range(int(loops)):
    print(f"Loop: {loop}")
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
        for box, band, wlan_id in [(box1, "2.4", 1), (box1, "5", 2)]:
            devices = box.get_associated_devices(wlan_id)
            download_speed = get_download_speed(box2, interval=snapshot_interval)
            for i, d in enumerate(devices):
                if debug2:
                    print(d["NewAssociatedDeviceMACAddress"],
                        d["NewAssociatedDeviceIPAddress"],
                        band,i,
                        d["NewAssociatedDeviceAuthState"],
                        d["NewX_AVM-DE_SignalStrength"],
                        d["NewX_AVM-DE_Speed"],
                        f"{download_speed / 1024:.2f} kB/s")
                # in CSV schreiben
                with open(output_csv, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        d["NewAssociatedDeviceMACAddress"],
                        d["NewAssociatedDeviceIPAddress"],
                        band,
                        d["NewAssociatedDeviceAuthState"],
                        d["NewX_AVM-DE_SignalStrength"],
                        d["NewX_AVM-DE_Speed"],
                        f"{download_speed / 1024:.2f} kB/s"])
            if debug2:        
                print("Daten in CSV geschrieben.")
        
        # 3 Snapshots sammeln
    for i in range(3):
        time.sleep(snapshot_interval)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
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
            filename = f"{timestamp2}_{damping}_Snapshot_{i}.jpg"
            smaller = cv2.resize(snapshots[i], None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            cv2.imwrite(filename, smaller)
        for i in range(2):
            filename = f"{timestamp2}_{damping}_{diff_values[i]}_Diff_{i}.jpg"
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

with open("CV Messung.txt", "a") as f:
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

            