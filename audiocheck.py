import subprocess
import numpy as np
import wave
import time
import sys

stream_url = "http://192.168.175.6:8080/hdmi"

def capture_audio(filename="audio.wav", duration=1):
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

if __name__ == "__main__":
    while True:
        capture_audio()
        rms, has_sound = check_audio()

        print(f"Aktuelle Lautstärke (RMS): {rms:.2f}")

        if not has_sound:
            print("❌ Kein Ton erkannt – Skript wird beendet.")
            sys.exit(0)

        time.sleep(1)
