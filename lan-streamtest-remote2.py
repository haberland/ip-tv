#! /usr/bin/python
import cv2
import time
import numpy as np
import subprocess
import requests
from datetime import datetime
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import html
import csv
from typing import Optional, Dict, List
import wave


# --- Einstellungen ---
attenuator_ip = "192.168.1.101"
attenuator= True
fakercu_ip = "192.168.175.19"
fakercu= True
# URL des HDMI-Streams
stream_url = "http://192.168.175.6:8080/hdmi"

start_db = 40.0
stop_db = 60.0
step_db = 0.25

settle_time = 15          # Sekunden warten nach neuer Dämpfung
snapshot_interval = 1     # Sekunden zwischen Snapshots und gleichzeitig download Geschwindigkeit und Tonauswertung berechnung
threshold = 250000        # Schwellenwert für Diff

audiocapture = True

# Log-Bild skalieren um größes zu verkeinern
scale = 0.5  # 50 % der Originalgröße

output_csv = "Messverlauf.csv"
testergebnis = "Testergebnisse.csv"
writecsv= True

debug= True

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
    
    if audiocapture:
        # Audio aufnehmen während des Intervalls
        capture_audio(duration=interval)
    else:
        time.sleep(interval)

    xml2 = fritz._soap_request(service, location, action, body)
    bytes2 = int(_find_tag_text(xml2, "NewTotalBytesReceived") or 0)

    return (bytes2 - bytes1) / interval  # Bytes pro Sekunde

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
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} [FakeRCU] Key {keycode} erfolgreich gesendet.")
    except requests.RequestException as e:
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} [FakeRCU] Fehler beim Senden von Key {keycode}: {e}")

def capture_audio(filename="audio.wav", duration=snapshot_interval):
    """
    Nimmt für 'duration' Sekunden Audio aus dem Stream auf und speichert als WAV.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", stream_url,
        "-t", str(duration),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        filename
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check_audio(filename="audio.wav", threshold=50):
    """
    Prüft, ob Ton vorhanden ist anhand des RMS-Pegels.
    """
    with wave.open(filename, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16)

    # RMS berechnen
    rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
    return rms, rms > threshold

####

box1 = FritzTR064("192.168.175.21", "jogger0413")
box2 = FritzTR064("192.168.175.1", "jacht6676")

# User automatisch holen
username1= box1.fetch_username()
username2= box2.fetch_username()

if debug:
    currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"{currenttime} Box1 User: {username1}, Box2 User: {username2}")

if writecsv:
    # CSV vorbereiten
    timestamp2 = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_csv = f"{timestamp2}-Messverlauf.csv"
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "NewAssociatedDeviceMACAddress", "NewAssociatedDeviceIPAddress", "Band", "NewAssociatedDeviceAuthState", "AVM-DE_SignalStrength", "AVM-DE_WLAN-Speed", "DownloadSpeed_kBps", "RMS"])
    #with open(testergebnis, "w", newline="") as f:
    #    writer = csv.writer(f)
    #    writer.writerow(["Timestamp", "Start dB", "Stop dB", "Step dB", "settle time", "snapshot interval", "threshold", "damping","Diff"])

snapshots = []
greyshots = []
timestamps = []
audiostreams = []

if debug:
    currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"{currenttime} [Setup] Wecke Stream...")
# --- Dämpfung einstellen ---
if attenuator:
    cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{start_db}"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if debug:
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} [Setup] Dämpfung gesetzt: {start_db} dB")
    time.sleep(5)
if fakercu:
    send_key("25")
    if debug:
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} [Setup] 5 Sekunden warten...")
    time.sleep(5)
    send_key("27")

# Stream öffnen
cap = cv2.VideoCapture(stream_url)
if not cap.isOpened():
    currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"{currenttime} [Error] Grabber konnte nicht geöffnet werden!")
    if writecsv:
        with open(output_csv, "a") as f:
            print("[Error] Grabber konnte nicht geöffnet werden!", file=f)
    exit(1)

timestamp2 = datetime.now().strftime("%Y%m%d-%H%M%S")

if debug:
    currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"{currenttime} [Setup] Starte Stream-Überwachung...")
snapshots.clear()
for i in range(3):
    time.sleep(snapshot_interval)
    ret, frame = cap.read()
    if not ret:
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} [Error] Kein Frame gelesen → Stream tot.")
        if writecsv:
            with open(output_csv, "a") as f:
                print("[Error] Kein Frame gelesen → Stream tot.", file=f)
        cap.release()
        exit(1)
    snapshots.append(frame)

    filename = f"Snapshot {i}.jpg"
    cv2.imwrite(filename, snapshots[i])
    snapshots.append(frame)

damping = start_db
while damping <= stop_db:
    snapshots.clear()
    greyshots.clear()
    timestamps.clear()
    audiostreams.clear()

    if attenuator:
        # --- Dämpfung einstellen ---
        cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{damping:.2f}"]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if debug:
            currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            print(f"{currenttime} [Testing] Dämpfung gesetzt: {damping:.2f} dB")
        # --- Wartezeit nach Dämpfungsänderung ---
        time.sleep(settle_time)

    # 3 Snapshots sammeln
    for i in range(3):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        ret, frame = cap.read()
        if not ret:
            print(f"{timestamp} [Error] Kein Frame gelesen → Stream tot.")
            if writecsv:
                with open(output_csv, "a") as f:
                    print("[Error] Kein Frame gelesen → Stream tot.", file=f)
            cap.release()
            exit(1)
        download_speed = get_download_speed(box2, interval=snapshot_interval)
        snapshots.append(frame)
        timestamps.append(timestamp)
        filename = f"Snapshot {i}.jpg"
        cv2.imwrite(filename, snapshots[i])
        greyshot = cv2.cvtColor(snapshots[i], cv2.COLOR_BGR2GRAY)
        filename = f"Snapshot {i} grey.jpg"
        greyshots.append(greyshot)
        cv2.imwrite(filename, greyshots[i])
        if debug:
            currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            print(f"{currenttime} {timestamp} [Testing] Snapshot {i+1} aufgenommen")

        if audiocapture:
            rms, has_sound = check_audio()
            audiostreams.append(rms)
        if debug:
            currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            if has_sound:
                print(f"{currenttime} [Audio] Aktuelle Lautstärke (RMS): {rms:.2f}")
            else:
                print(f"{currenttime} [Audio] ❌ Kein Ton erkannt (RMS: {rms:.2f})")

        for box, band, wlan_id in [(box1, "2.4", 1), (box1, "5", 2)]:
            devices = box.get_associated_devices(wlan_id)
            for i, d in enumerate(devices):
                if debug:
                    print(f"{timestamp}",
                        d["NewAssociatedDeviceMACAddress"],
                        d["NewAssociatedDeviceIPAddress"],
                        band,i,
                        d["NewAssociatedDeviceAuthState"],
                        d["NewX_AVM-DE_SignalStrength"],
                        d["NewX_AVM-DE_Speed"],
                        f"{download_speed / 1024:.2f} kB/s",
                        f"{rms:.2f}")
                if writecsv:
                    # in CSV schreiben
                    with open(output_csv, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([f"{timestamp}",
                            d["NewAssociatedDeviceMACAddress"],
                            d["NewAssociatedDeviceIPAddress"],
                            band,
                            d["NewAssociatedDeviceAuthState"],
                            d["NewX_AVM-DE_SignalStrength"],
                            d["NewX_AVM-DE_Speed"],
                            f"{download_speed / 1024:.2f} kB/s"
                            f"{rms:.2f}"])
                    if debug:
                        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        print(f"{currenttime} [Testing] Daten in CSV geschrieben.")

    # Differenzen berechnen
    diffs = []
    diff_values = []
    for i in range(2):
        diff = cv2.absdiff(greyshots[i], greyshots[i+1])
        diffs.append(diff)
        diff_value = np.sum(diff)
        diff_values.append(diff_value)
        filename = f"Snapshot {i+1} grey diff {diff_value}.jpg"
        cv2.imwrite(filename, diff)
        if debug:
            currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            print(f"{currenttime} [Testing] Diff {i+1}: {diff_value}")
    
    if not audiocapture:
        rms, has_sound = 1, False

    print(f"#######AUDIO: {audiostreams[0]:.2f}, {audiostreams[0]:.2f}")

    # Prüfen ob Stream hängt / alle kleiner Schwellwert
    #if all(d < threshold for d in diffs):
    # Prüfen ob Stream hängt / einer kleiner Schwellwert
    #if any(d < threshold for d in diff_values):
    if all(d < threshold for d in diff_values) and not all(a > 1 for a in audiostreams):    
        if debug:        
            currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            print(f"{currenttime} [Result] Stream hängt → Daten werden gesichert.")
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
    if fakercu and damping % 10 == 0:
        send_key("26")
        time.sleep(3)
        send_key("24")
    if attenuator:
        damping += step_db

cap.release()
if debug:
    print(f"+-------------------------------+")
    print(f"| Messung beendet, Stream hängt |")
    print(f"+-------------------------------+")
    print(f"{timestamps[0]}, Dämpfung: {damping}, Diff: {diff_value}")
    print(f"")

if writecsv:
    with open(testergebnis, "a") as f:
        print(f"{timestamps[0]},{start_db},{stop_db},{step_db},{settle_time},{snapshot_interval},{threshold},{damping},{diff_value},{rms}", file=f)

if attenuator:
    cmd = ["curl", f"http://{attenuator_ip}/execute.php?SAA+{start_db}"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if debug:
        currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        print(f"{currenttime} Dämpfung gesetzt: {start_db} dB")
    time.sleep(5)

if fakercu:    
    send_key("25")
    time.sleep(5)
    send_key("27")

if debug:
    currenttime= datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"{currenttime} [Goodbye] Messung beendet → Programm beendet.")
exit(0)