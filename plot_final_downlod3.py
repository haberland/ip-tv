import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
import os
import sys

# CSV-Datei laden
file_path = os.path.expanduser(sys.argv[1])
df = pd.read_csv(file_path)

# Timestamp konvertieren
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%d.%m.%Y %H:%M:%S")

# Mapping MAC → Gerätename
mac_map = {
    "B4:96:A5:AD:2C:29": "iPhone 16",
    "4A:70:45:19:E7:03": "1&1STB",
    "AC:F4:2C:68:73:88": "Innoptia"
}
df["Device"] = df["MACAddress"].map(mac_map).fillna(df["MACAddress"])

# Farbpalette pro Gerät und GHz
color_map = {
    ("iPhone 16", 2.4): "grey",
    ("iPhone 16", 5): "grey",
    ("1&1STB", 2.4): "blue",
    ("1&1STB", 5): "blue",
    ("Innoptia", 2.4): "red",
    ("Innoptia", 5): "red"
}

fig, ax1 = plt.subplots(figsize=(32, 6))

# Zusätzliche Y-Achse für C4
ax2 = ax1.twinx()
# Eine weitere Y-Achse für Downspeed
ax3 = ax1.twinx()
ax3.spines['right'].set_position(('outward', 60))

# --- Label-Tracker für Legende ---
plotted_labels = set()

# Für jedes Gerät plotten
for device, ddf in df.groupby("Device"):
    ddf = ddf.sort_values("Timestamp")

    # Sessions trennen bei >45s Lücke
    ddf["gap"] = ddf["Timestamp"].diff() > timedelta(seconds=30)
    session_ids = ddf["gap"].cumsum()

    for session_id, session in ddf.groupby(session_ids):
        if session.empty:
            continue

        # --- Session weiter splitten nach GHz-Wechsel ---
        session["freq_change"] = session["GHz"].ne(session["GHz"].shift()).cumsum()

        for sub_id, sub in session.groupby("freq_change"):
            if sub.empty:
                continue

            freq = sub.iloc[0]["GHz"]
            color = color_map.get((device, freq), "black")
            linestyle = "--" if freq == 2.4 else "-"

            label = None
            if (device, freq) not in plotted_labels:
                label = f"{device} {freq}GHz"
                plotted_labels.add((device, freq))

            # Signalstärke-Linie (linke Y-Achse)
            ax1.plot(sub["Timestamp"], sub["AVM-DE_SignalStrength"],
                     label=label,
                     color=color, linestyle=linestyle, alpha=0.9)

            # Marker für Bandwechsel (Startpunkt jeder Sub-Session)
            start = sub.iloc[0]
            ax1.plot(start["Timestamp"], start["AVM-DE_SignalStrength"],
                     marker="o", color=color, markersize=5, zorder=5)
            ax1.annotate(f"{device}\n{start['GHz']}GHz",
                         xy=(start["Timestamp"], start["AVM-DE_SignalStrength"]),
                         xytext=(5, -5), textcoords="offset points",
                         fontsize=5, color=color)

            # C4-Linie (rechte Y-Achse)
            ax2.plot(sub["Timestamp"], sub["C4"],
                     linestyle="--", color=color, alpha=0.6)

        # Endpunkt der gesamten Session markieren
        end = session.iloc[-1]
        ax1.annotate(f"{device}\n{end['Timestamp']}\n"
                     f"{end['AVM-DE_Speed']} Mbps, "
                     f"{end['AVM-DE_SignalStrength']} dB, "
                     f"{end['GHz']}GHz, "
                     f"D={end['C1']}",
                     xy=(end["Timestamp"], end["AVM-DE_SignalStrength"]),
                     xytext=(0, -15), textcoords="offset points",
                     fontsize=5, color=color)

# --- Downloadspeed nur einmal plotten (akkumuliert) ---
ds_mbps = (df.groupby("Timestamp")["ds"].first() * 8) / 1_000_000
ax3.plot(ds_mbps.index, ds_mbps.values,
         linestyle="--", dashes=(5, 5, 2, 2),
         color="green", alpha=0.5,
         label="Downspeed (gesamt)")

# X-Achse: 5-Minuten Schritte
ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
fig.autofmt_xdate()

# Achsentitel
ax1.set_title("WiFi Signalstärke in Prozent, Dämpfung in dB & Downspeed Mb/s im Verlauf")
ax1.set_xlabel("Zeit")
ax1.set_ylabel("Signalstärke in Prozent")
ax2.set_ylabel("Dämpfung in dB")
ax3.set_ylabel("Downspeed (Mb/s, akkumuliert)")

# Legende
lines1, labels1 = ax1.get_legend_handles_labels()
lines3, labels3 = ax3.get_legend_handles_labels()
ax1.legend(lines1 + lines3, labels1 + labels3, loc='upper left')

ax1.grid(True)
fig.tight_layout()

# Datei speichern
plt.savefig("wifi_signal_c4_downspeed3.png", dpi=300)
