#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Variablen
# -----------------------------
tr064_proto="http"
tr064_port="49000"
fritzbox_ip="192.168.175.21"
fritzbox_ip2="192.168.175.1"
fritz_user=""
fritz_pass="heini7465"
fritz_user2=""
fritz_pass2="jacht6676"

attenuator=0
start=47.0
end=7.5
step=0.25
sleeping=5
zapping=0
write=true

# -----------------------------
# Funktion: User & Passwort ermitteln
# -----------------------------
get_fritz_credentials() {
    local uri="urn:dslforum-org:service:LANConfigSecurity:1"
    local location="/upnp/control/lanconfigsecurity"
    local action="X_AVM-DE_GetUserList"

    local soap_body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
                xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body>
        <u:X_AVM-DE_GetUserList xmlns:u="urn:dslforum-org:service:LANConfigSecurity:1"/>
      </s:Body>
    </s:Envelope>'

    local response
    response=$(curl -s -k -m 5 \
      "${tr064_proto}://${fritzbox_ip}:${tr064_port}${location}" \
      -H "Content-Type: text/xml; charset=\"utf-8\"" \
      -H "SoapAction:${uri}#${action}" \
      -d "$soap_body")

    # Inneres XML aus <NewX_AVM-DE_UserList>
    local inner
    inner=$(echo "$response" | tr -d '\n' | sed -n 's:.*<NewX_AVM-DE_UserList>\(.*\)</NewX_AVM-DE_UserList>.*:\1:p')
    inner=$(echo "$inner" | sed 's/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g; s/&apos;/\x27/g; s/&amp;/\&/g')

    fritz_user=$(echo "$inner" | grep -o '<Username[^>]*>[^<]*</Username>' | sed -E 's:.*>([^<]+)<.*:\1:' | head -n1)
}

get_fritz_credentials2() {
    local uri="urn:dslforum-org:service:LANConfigSecurity:1"
    local location="/upnp/control/lanconfigsecurity"
    local action="X_AVM-DE_GetUserList"

    local soap_body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
                xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body>
        <u:X_AVM-DE_GetUserList xmlns:u="urn:dslforum-org:service:LANConfigSecurity:1"/>
      </s:Body>
    </s:Envelope>'

    local response
    response=$(curl -s -k -m 5 \
      "${tr064_proto}://${fritzbox_ip2}:${tr064_port}${location}" \
      -H "Content-Type: text/xml; charset=\"utf-8\"" \
      -H "SoapAction:${uri}#${action}" \
      -d "$soap_body")

    # Inneres XML aus <NewX_AVM-DE_UserList>
    local inner
    inner=$(echo "$response" | tr -d '\n' | sed -n 's:.*<NewX_AVM-DE_UserList>\(.*\)</NewX_AVM-DE_UserList>.*:\1:p')
    inner=$(echo "$inner" | sed 's/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g; s/&apos;/\x27/g; s/&amp;/\&/g')

    fritz_user2=$(echo "$inner" | grep -o '<Username[^>]*>[^<]*</Username>' | sed -E 's:.*>([^<]+)<.*:\1:' | head -n1)
}
# -----------------------------
# Funktion: SOAP Request
# -----------------------------
soap_request() {
    local service="$1"
    local location="$2"
    local action="$3"
    local body="$4"

    curl -sS -k -m 5 --anyauth \
        -u "${fritz_user}:${fritz_pass}" \
        "${tr064_proto}://${fritzbox_ip}:${tr064_port}${location}" \
        -H 'Content-Type: text/xml; charset="utf-8"' \
        -H "SoapAction:${service}#${action}" \
        -d "$body"
}

soap_request2() {
    local service="$1"
    local location="$2"
    local action="$3"
    local body="$4"

    curl -sS -k -m 5 --anyauth \
        -u "${fritz_user2}:${fritz_pass2}" \
        "${tr064_proto}://${fritzbox_ip2}:${tr064_port}${location}" \
        -H 'Content-Type: text/xml; charset="utf-8"' \
        -H "SoapAction:${service}#${action}" \
        -d "$body"
}

# -----------------------------
# Beispiel: WLAN Status holen
# -----------------------------
get_wlan_status() {
    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="GetInfo"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

get_associations() {
    local instance="$1"

    local service="urn:dslforum-org:service:WLANConfiguration:$instance"
    local location="/upnp/control/wlanconfig$instance"
    local action="GetTotalAssociations"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}


# -----------------------------
# WLAN ändern
# -----------------------------
set_wlan_instance() {
    local instance="$1"
    local new_ssid="$2"

    local service="urn:dslforum-org:service:WLANConfiguration:$instance"
    local location="/upnp/control/wlanconfig$instance"

    echo "⚙️  Ändere WLAN-Instanz $instance ..."

    # SSID setzen
    local action="SetSSID"
    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'">
          <NewSSID>'"$new_ssid"'</NewSSID>
        </u:'"$action"'>
      </s:Body>
    </s:Envelope>'
    soap_request "$service" "$location" "$action" "$body"
}

set_wlan_password() {
    local new_pw="$1"

    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="SetSecurityKeys"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <SOAP-ENV:Envelope
      xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
      SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <SOAP-ENV:Body>
        <m:'"$action"' xmlns:m="'"$service"'">
          <NewKeyPassphrase>'"$new_pw"'</NewKeyPassphrase>
        </m:'"$action"'>
      </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>'

    echo "Ändere WLAN-Passwort in $new_pw..."
    soap_request "$service" "$location" "$action" "$body"
    echo "WLAN-Passwort gesetzt."
}


get_wlan_password() {
    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="GetSecurityKeys"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}


get_generic_associated_device_info() {
    local instance="$1"
    local wlan_instance="${2:-1}"  # Standard: wlanconfig1

    local service="urn:dslforum-org:service:WLANConfiguration:$wlan_instance"
    local location="/upnp/control/wlanconfig$wlan_instance"
    local action="GetGenericAssociatedDeviceInfo"

    local body='<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:'"$action"' xmlns:u="'"$service"'">
      <NewAssociatedDeviceIndex>'"$instance"'</NewAssociatedDeviceIndex>
    </u:'"$action"'>
  </s:Body>
</s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

GetSpecificAssociatedDeviceInfo() {
    local instance="$1"
    local wlan_instance="${2:-1}"  # Standard: wlanconfig1

    local service="urn:dslforum-org:service:WLANConfiguration:$wlan_instance"
    local location="/upnp/control/wlanconfig$wlan_instance"
    local action="GetSpecificAssociatedDeviceInfo"

    local body='<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:'"$action"' xmlns:u="'"$service"'">
      <NewAssociatedDeviceMACAddress>'"$instance"'</NewAssociatedDeviceMACAddress>
    </u:'"$action"'>
  </s:Body>
</s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

get_IPTV_optimized() {
    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="X_AVM-DE_GetIPTVOptimized"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

get_statistics() {
    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="GetStatistics"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

get_packet_statistics() {
    local service="urn:dslforum-org:service:WLANConfiguration:1"
    local location="/upnp/control/wlanconfig1"
    local action="GetPacketStatistics"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

ausgabe(){

# Beispiel 1: get_wlan_status
xml_wlan=$(get_wlan_status)
echo "=== Router WLAN Status ==="
parse_xml "$xml_wlan"

echo
echo
echo "=== Client WLAN Status ==="

# Anzahl der verbundenen 2,4GHz Geräte ermitteln
xml_total=$(get_associations 1)
total2=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
echo "Gefundene Clienten 2,4GHz: $total2"
echo "Index, MACAddress, IPAddress, DeviceAuthState, AVM-DE_Speed, AVM-DE_SignalStrength, AVM-DE_ChannelWidth"

for ((i=0; i<total2; i++)); do
    xml=$(get_generic_associated_device_info "$i")
    # Werte extrahieren
    mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
    ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
    auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
    speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
    signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
    width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

    # Zeile ausgeben
    echo -e "$i\t$mac\t$ip\t$auth\t$speed\t$signal\t$width"
done

echo 
# Anzahl der verbundenen 5GHz Geräte ermitteln
xml_total=$(get_associations 2)
total5=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
echo "Gefundene Clienten 5GHz: $total5"
echo "Index, MACAddress, IPAddress, DeviceAuthState, AVM-DE_Speed, AVM-DE_SignalStrength, AVM-DE_ChannelWidth"

for ((i=0; i<total5; i++)); do
    xml=$(get_generic_associated_device_info "$i" 2)
    # Werte extrahieren
    mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
    ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
    auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
    speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
    signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
    width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

    # Zeile ausgeben
    echo -e "$i\t$mac\t$ip\t$auth\t$speed\t$signal\t$width"
done 
}

parse_xml() {
    local xml_response="$1"
    echo -e "Feld\tWert"
    echo "$xml_response" | xmllint --xpath '//*[starts-with(name(), "New")]' - 2>/dev/null | \
    tr '<' '\n' | grep '^New' | sed -E 's|/?>|\t|' | awk -F'\t' '{print $1 "\t" $2}'
}

send_key() {
  local keycode=$1
  curl -s "http://192.168.175.19:8181/" \
    -X POST \
    -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
    --data-raw "keycode=$keycode&hidden=on" > /dev/null
}

hoch_runter(){
	echo Hoch-Runter
    	if [[ "$write" == "1" || "$write" == "true" ]]; then
        	timestamp=$(date '+%Y%m%d_%H%M%S')
        	filename="wlan_${timestamp}.csv"
    	fi
	if [[ "$attenuator" == "1" || "$attenuator" == "true" ]]; then
	    	echo Turn down the attenuator and wait 1 seconds.
    		echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size"
	fi
    	if [[ "$write" == "1" || "$write" == "true" ]]; then
        	echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size" >> "$filename"
    	fi

	while true; do
    		# Hochzählen von 0.0 -> 95.0
    		val=$end
    		while (( $(echo "$val <= $start" | bc -l) )); do
        		printf "%.2f\n" "$val"
        		val=$(echo "$val + $step" | bc -l)
        		get24ghz
                        get5ghz
			set_attenuator $val
			if [[ "$zapping" == "1" || "$write" == "true" ]]; then
				send_key 24
			fi
			sleep $sleeping  # optional
    		done

		# Runterzählen von 95.0 -> 0.0
                val=$start
                while (( $(echo "$val >= $end" | bc -l) )); do
                        printf "%.2f\n" "$val"
                        val=$(echo "$val - $step" | bc -l)
                        get24ghz
                        get5ghz
                        set_attenuator $val
			if [[ "$zapping" == "1" || "$write" == "true" ]]; then
        	                send_key 24
			fi
                        sleep $sleeping  # optional
                done

	done
}

get24ghz(){
	timestamp=$(date '+%d.%m.%Y %H:%M:%S')
        # Anzahl der verbundenen 5GHz Geräte ermitteln
        xml_total=$(get_associations 1)
        total2=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
        for ((i=0; i<total2; i++)); do
            xml=$(get_generic_associated_device_info "$i")
            # Werte extrahieren
            mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
            ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
            auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
            speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
            signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
            width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

            # Zeile ausgeben
            echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,2.4,$(get_attenuator_status),$(get_downstream_current_utilization)"
            if [[ "$write" == "1" || "$write" == "true" ]]; then
                echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,2.4,$(get_attenuator_status),$(get_downstream_current_utilization)" >> "$filename"
            fi
        done

}

get5ghz(){
	timestamp=$(date '+%d.%m.%Y %H:%M:%S')
	# Anzahl der verbundenen 5GHz Geräte ermitteln
        xml_total=$(get_associations 2)
        total5=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
        for ((i=0; i<total5; i++)); do
            timestamp=$(date '+%d.%m.%Y %H:%M:%S')
            xml=$(get_generic_associated_device_info "$i" 2)
            # Werte extrahieren
            mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
            ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
            auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
            speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
            signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
            width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

            # Zeile ausgeben
            echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,5,$(get_attenuator_status),$(get_downstream_current_utilization)"
            if [[ "$write" == "1" || "$write" == "true" ]]; then
                echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,5,$(get_attenuator_status),$(get_downstream_current_utilization)"  >> "$filename"
            fi
        done

}


schleife(){
    echo
    echo 
    echo Teststart
    if [[ "$write" == "1" || "$write" == "true" ]]; then
        timestamp=$(date '+%Y%m%d_%H%M%S')
        filename="wlan_${timestamp}.csv"
    fi
    echo Turn down the attenuator and wait 1 seconds.
    echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size"
    if [[ "$write" == "1" || "$write" == "true" ]]; then
        echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size" >> "$filename"
    fi
    for ((loop=0; loop<10; loop++)); do
        timestamp=$(date '+%d.%m.%Y %H:%M:%S')
        # Anzahl der verbundenen 5GHz Geräte ermitteln
        xml_total=$(get_associations 1)
        total2=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
        for ((i=0; i<total2; i++)); do
            xml=$(get_generic_associated_device_info "$i")
            # Werte extrahieren
            mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
            ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
            auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
            speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
            signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
            width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

            # Zeile ausgeben
            echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,2.4,$(get_attenuator_status),$(get_current_downloadspeed)"
            if [[ "$write" == "1" || "$write" == "true" ]]; then
                echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,2.4,$(get_attenuator_status),$(get_current_downloadspeed)" >> "$filename"
            fi
        done

        # Anzahl der verbundenen 5GHz Geräte ermitteln
        xml_total=$(get_associations 2)
        total5=$(echo "$xml_total" | xmllint --xpath 'string(//NewTotalAssociations)' - 2>/dev/null)
        for ((i=0; i<total5; i++)); do
            timestamp=$(date '+%d.%m.%Y %H:%M:%S')
            xml=$(get_generic_associated_device_info "$i" 2)
            # Werte extrahieren
            mac=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceMACAddress)' - 2>/dev/null)
            ip=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceIPAddress)' - 2>/dev/null)
            auth=$(echo "$xml" | xmllint --xpath 'string(//NewAssociatedDeviceAuthState)' - 2>/dev/null)
            speed=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_Speed)' - 2>/dev/null)
            signal=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_SignalStrength)' - 2>/dev/null)
            width=$(echo "$xml" | xmllint --xpath 'string(//NewX_AVM-DE_ChannelWidth)' - 2>/dev/null)

            # Zeile ausgeben
            echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,5,$(get_attenuator_status),$(get_current_downloadspeed)"
            if [[ "$write" == "1" || "$write" == "true" ]]; then
                echo -e "$timestamp,$i,$mac,$ip,$auth,$speed,$signal,$width,5,$(get_attenuator_status),$(get_current_downloadspeed)"  >> "$filename"
            fi
        done
	sleep 1
    done
}

get_attenuator_status() {
        resp=$(curl -s "http://192.168.1.101/execute.php?STATUS")
        values=$(echo "$resp" | sed 's/\r//g' | awk -F': ' '/Channel/ {print $2}' | xargs | tr ' ' ',')
        echo "$values"
}

set_attenuator() {
	local dbm="$1"
    	if [[ "$attenuator" == "1" || "$attenuator" == "true" ]]; then
        	resp=$(curl -s "http://192.168.1.101/execute.php?SAA+$dbm")
    	fi
}

get_common_link_properties() {
    local service="urn:dslforum-org:service:WANCommonInterfaceConfig:1"
    local location="/upnp/control/wancommonifconfig1"
    local action="GetCommonLinkProperties"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo "$resp"
}

get_online_monitor() {
    local service="urn:dslforum-org:service:WANCommonInterfaceConfig:1"
    local location="/upnp/control/wancommonifconfig1"
    local action="X_AVM-DE_GetOnlineMonitor"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'">
      <NewSyncGroupIndex>'"0"'</NewSyncGroupIndex>
    </u:'"$action"'>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")
    echo $resp
}

get_current_downloadspeed() {
    local service="urn:dslforum-org:service:WANCommonInterfaceConfig:1"
    local location="/upnp/control/wancommonifconfig1"
    local action="X_AVM-DE_GetOnlineMonitor"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'">
      <NewSyncGroupIndex>'"3"'</NewSyncGroupIndex>
    </u:'"$action"'>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request "$service" "$location" "$action" "$body")

    # Extrahiere nur den Inhalt von <Newds_current_bps>
    ds_values=$(echo "$resp" | xmllint --xpath 'string(//Newds_current_bps)' - 2>/dev/null)

    # Ersten Wert holen (vor dem ersten Komma)
    first_value=$(echo "$ds_values" | cut -d',' -f1)

    echo "$first_value,bps"
}


get_downstream_current_utilization() {
    local service="urn:dslforum-org:service:WANCommonInterfaceConfig:1"
    local location="/upnp/control/wancommonifconfig1"
    local action="GetCommonLinkProperties"

    local body='<?xml version="1.0" encoding="utf-8"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
      <s:Body>
        <u:'"$action"' xmlns:u="'"$service"'"/>
      </s:Body>
    </s:Envelope>'

    local resp
    resp=$(soap_request2 "$service" "$location" "$action" "$body")
    #echo "$resp"
    # Downstream-Werte extrahieren und Durchschnitt berechnen
    downstream_data=$(echo "$resp" | grep '<NewX_AVM-DE_DownstreamCurrentUtilization>' | sed 's/.*<NewX_AVM-DE_DownstreamCurrentUtilization>\(.*\)<\/NewX_AVM-DE_DownstreamCurrentUtilization>.*/\1/')
    #downstream_average=$(calculate_average "$downstream_data")
    #echo "Durchschnittliche Downstream-Auslastung: $downstream_average"
    #echo $downstream_data
        #echo $(echo $downstream_data | cut -d',' -f1 )
        echo $(echo $downstream_data | cut -d',' -f1,2 | awk -F',' '{print ($1 + $2) / 2 + 0.5 }')
}


sniffing(){
        if [[ "$write" == "1" || "$write" == "true" ]]; then
                timestamp=$(date '+%Y%m%d_%H%M%S')
                filename="wlan_${timestamp}.csv"
                echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size"
                echo "Timestamp,DeviceIndex,MACAddress,IPAddress,DeviceAuthState,AVM-DE_Speed,AVM-DE_SignalStrength,AVM-DE_ChannelWidth,GHz,C1,C2,C3,C4,ds,size" >> "$filename"
        fi
        while true; do
		        get24ghz
            get5ghz
            sleep $sleeping  # optional
        done
}




# -----------------------------
# MAIN
# -----------------------------
get_fritz_credentials
ausgabe
#schleife
##hoch_runter
sniffing
#get_attenuator_status

#get_current_downloadspeed

#GetOnlineMonitor
#get_wlan_status
#get_associations
#get_wlan_password
#get_generic_associated_device_info 0
#GetSpecificAssociatedDeviceInfo "FE:15:C8:01:80:4F"
#get_IPTV_optimized
#get_statistics
#get_packet_statistics
#get_common_link_properties

#set

#ssid="Test2TestLAN5"
#y
#pw="MeinSicheresPasswort123"


#set_wlan_instance 1 "$ssid"
#set_wlan_instance 2 "$ssid"

#set_wlan_password "$pw"
echo  ende
