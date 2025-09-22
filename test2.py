import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import html
import time
from typing import Optional, Dict, List

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


# -----------------------------
# Hauptprogramm
# -----------------------------
if __name__ == "__main__":
    # Zwei Fritzboxen definieren
    box1 = FritzTR064("192.168.175.21", "heini7465")
    box2 = FritzTR064("192.168.175.1", "jacht6676")

    # User automatisch holen
    box1.fetch_username()
    box2.fetch_username()

    download_speed = get_download_speed(box2, interval=1.0)
    print(f"Aktuelle Downloadgeschwindigkeit: {download_speed / 1024:.2f} kB/s")

    #while True:
    #    for box, band, wlan_id in [(box1, "2.4 GHz", 1), (box1, "5 GHz", 2)]:
    #        devices = box.get_associated_devices(wlan_id)
    #        for i, d in enumerate(devices):
    #            print(f"{box.ip} [{band}] Index {i}:",
    #                  d["NewAssociatedDeviceMACAddress"],
    #                  d["NewAssociatedDeviceIPAddress"],
    #                  d["NewAssociatedDeviceAuthState"],
    #                  d["NewX_AVM-DE_SignalStrength"],
    #                  d["NewX_AVM-DE_Speed"])
    #    time.sleep(5)
