import requests
import xml.etree.ElementTree as ET
import html

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


if __name__ == "__main__":
    get_fritz_credentials()
    print("Fritzbox1 User:", fritz_user)

    get_fritz_credentials2()
    print("Fritzbox2 User:", fritz_user2)
