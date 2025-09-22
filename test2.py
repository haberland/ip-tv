import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import html
import time
from typing import Optional, Dict

# -----------------------------
# Variablen
# -----------------------------
tr064_proto = "http"
tr064_port = "49000"
fritzbox_ip = "192.168.175.21"
fritzbox_ip2 = "192.168.175.1"

fritz_user = ""
fritz_pass = "heini7465"
fritz_user2 = ""
fritz_pass2 = "jacht6676"

def get_fritz_credentials():
    global fritz_user
    uri = "urn:dslforum-org:service:LANConfigSecurity:1"
    location = "/upnp/control/lanconfigsecurity"
    action = "X_AVM-DE_GetUserList"

    soap_body = """<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
                xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body>
        <u:X_AVM-DE_GetUserList xmlns:u="urn:dslforum-org:service:LANConfigSecurity:1"/>
      </s:Body>
    </s:Envelope>"""

    url = f"{tr064_proto}://{fritzbox_ip}:{tr064_port}{location}"
    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SoapAction": f"{uri}#{action}"
    }

    response = requests.post(url, headers=headers, data=soap_body, verify=False, timeout=5)
    response.raise_for_status()

    # Inneres XML extrahieren
    inner = ""
    if "<NewX_AVM-DE_UserList>" in response.text:
        start = response.text.find("<NewX_AVM-DE_UserList>") + len("<NewX_AVM-DE_UserList>")
        end = response.text.find("</NewX_AVM-DE_UserList>")
        inner = response.text[start:end]

    # HTML-Entities zurückwandeln (&lt; → <, &gt; → >, usw.)
    inner = html.unescape(inner)

    # Erstes <Username> extrahieren
    try:
        root = ET.fromstring(inner)
        for user in root.findall(".//Username"):
            fritz_user = user.text
            break
    except ET.ParseError:
        fritz_user = None

def get_fritz_credentials2():
    global fritz_user2
    uri = "urn:dslforum-org:service:LANConfigSecurity:1"
    location = "/upnp/control/lanconfigsecurity"
    action = "X_AVM-DE_GetUserList"

    soap_body = """<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
                xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body>
        <u:X_AVM-DE_GetUserList xmlns:u="urn:dslforum-org:service:LANConfigSecurity:1"/>
      </s:Body>
    </s:Envelope>"""

    url = f"{tr064_proto}://{fritzbox_ip2}:{tr064_port}{location}"
    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SoapAction": f"{uri}#{action}"
    }

    response = requests.post(url, headers=headers, data=soap_body, verify=False, timeout=5)
    response.raise_for_status()

    inner = ""
    if "<NewX_AVM-DE_UserList>" in response.text:
        start = response.text.find("<NewX_AVM-DE_UserList>") + len("<NewX_AVM-DE_UserList>")
        end = response.text.find("</NewX_AVM-DE_UserList>")
        inner = response.text[start:end]

    inner = html.unescape(inner)

    try:
        root = ET.fromstring(inner)
        for user in root.findall(".//Username"):
            fritz_user2 = user.text
            break
    except ET.ParseError:
        fritz_user2 = None

def soap_request(service, location, action, body):
    url = f"{tr064_proto}://{fritzbox_ip}:{tr064_port}{location}"
    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SoapAction": f"{service}#{action}"
    }
    response = requests.post(url, headers=headers, data=body,
                             auth=(fritz_user, fritz_pass),
                             verify=False, timeout=5)
    return response.text

def soap_request2(service, location, action, body):
    url = f"{tr064_proto}://{fritzbox_ip2}:{tr064_port}{location}"
    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SoapAction": f"{service}#{action}"
    }
    response = requests.post(url, headers=headers, data=body,
                             auth=(fritz_user2, fritz_pass2),
                             verify=False, timeout=5)
    return response.text

# --- Hilfsfunktionen ---
def _find_tag_text(xml: str, localname: str) -> Optional[str]:
    """
    Namespace-agnostisch nach <...LocalName> suchen und Text zurückgeben.
    (ElementTree gibt Tags mit {namespace}LocalName zurück, daher endswith())
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    for el in root.iter():
        if el.tag is None:
            continue
        # endswith erlaubt namespace-agnostische Suche
        if el.tag.endswith(localname):
            return (el.text or "").strip()
    return None

class FritzTR064:
    def __init__(self, ip: str, user: str, password: str, port: int = 49000, proto: str = "http"):
        self.ip = ip
        self.user = user
        self.password = password
        self.port = port
        self.proto = proto
        self.base = f"{self.proto}://{self.ip}:{self.port}"

    def soap_request(self, service: str, location: str, action: str, body: str, timeout: int = 5) -> str:
        """
        Macht einen SOAP-POST mit Digest-Auth.
        Wichtig: SOAPAction muss in Anführungszeichen gesendet werden: "<service>#<action>"
        """
        url = self.base + location
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            # SOAPAction benötigt laut TR-064 Doku das Format: "urn:...#Action"
            "SOAPAction": f'"{service}#{action}"',
            "User-Agent": "python-TR064-client/1.0"
        }
        resp = requests.post(url, headers=headers, data=body,
                             auth=HTTPDigestAuth(self.user, self.password),
                             timeout=timeout, verify=False)
        resp.raise_for_status()
        return resp.text

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
        xml = self.soap_request(service, location, action, body)
        val = _find_tag_text(xml, "NewTotalAssociations")
        try:
            return int(val) if val is not None else 0
        except ValueError:
            return 0

    def get_generic_associated_device_info(self, index: int, wlan_instance: int = 1) -> Dict[str, Optional[str]]:
        """
        Holt die Informationen für den Gerät-Index (NewAssociatedDeviceIndex).
        Achtung: Index ist numerisch (0 .. total-1).
        """
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
        xml = self.soap_request(service, location, action, body)
        # Felder, die häufig benötigt werden:
        keys = [
            "NewAssociatedDeviceMACAddress",
            "NewAssociatedDeviceIPAddress",
            "NewAssociatedDeviceAuthState",
            "NewX_AVM-DE_Speed",
            "NewX_AVM-DE_SignalStrength",
            "NewX_AVM-DE_ChannelWidth"
        ]
        result = {}
        for k in keys:
            result[k] = _find_tag_text(xml, k)
        result["_raw_xml"] = xml
        return result

if __name__ == "__main__":
    get_fritz_credentials()
#    print("Fritzbox1 User:", fritz_user)
    get_fritz_credentials2()
#    print("Fritzbox2 User:", fritz_user2)

    f = FritzTR064(fritzbox_ip, fritz_user, fritz_pass, port=tr064_port, proto=tr064_proto)
#    print("=== 2.4 GHz (WLANConfiguration:1) ===")
#    total24 = f.get_total_associations(1)
#    print("Total 2.4 GHz clients:", total24)
#    for i in range(total24):
#        info = f.get_generic_associated_device_info(i, wlan_instance=1)
#        print(f"Index {i}:", info["NewAssociatedDeviceMACAddress"],
#              info["NewAssociatedDeviceIPAddress"],
#              info["NewAssociatedDeviceAuthState"],
#              "2.4 GHz",
#              info["NewX_AVM-DE_SignalStrength"],
#              info["NewX_AVM-DE_Speed"])

#    print("\n=== 5 GHz (WLANConfiguration:2) ===")
#    total5 = f.get_total_associations(2)
#    print("Total 5 GHz clients:", total5)
#    for i in range(total5):
#        info = f.get_generic_associated_device_info(i, wlan_instance=2)
#        print(f"Index {i}:", info["NewAssociatedDeviceMACAddress"],
#              info["NewAssociatedDeviceIPAddress"],
#              info["NewAssociatedDeviceAuthState"],
#              "5.0 GHz",
#              info["NewX_AVM-DE_SignalStrength"],
#              info["NewX_AVM-DE_Speed"])

    while True:
        total24 = f.get_total_associations(1)
        for i in range(total24):
            info = f.get_generic_associated_device_info(i, wlan_instance=1)
            print(f"Index {i}:", info["NewAssociatedDeviceMACAddress"],
              info["NewAssociatedDeviceIPAddress"],
              info["NewAssociatedDeviceAuthState"],
              "2.4 GHz",
              info["NewX_AVM-DE_SignalStrength"],
              info["NewX_AVM-DE_Speed"])
        total5 = f.get_total_associations(2)
        for i in range(total5):
            info = f.get_generic_associated_device_info(i, wlan_instance=2)
            print(f"Index {i}:", info["NewAssociatedDeviceMACAddress"],
              info["NewAssociatedDeviceIPAddress"],
              info["NewAssociatedDeviceAuthState"],
              "5.0 GHz",
              info["NewX_AVM-DE_SignalStrength"],
              info["NewX_AVM-DE_Speed"])
        time.sleep(5)