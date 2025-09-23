from pathlib import Path
import json

config_file = "config.json"

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
    text = input("Bitte gib einen Text ein: ")
    zahl_int = int(input("Bitte gib eine ganze Zahl ein: "))
    zahl_float = float(input("Bitte gib eine Kommazahl ein (z. B. 3,14): ").replace(",", "."))

    data = {
        "text": text,
        "zahl_int": zahl_int,
        "zahl_float": zahl_float
    }

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Daten wurden in {file_path} gespeichert")
    return data


# Beispielaufruf
daten = get_or_create_data(config_file)

print("\n\n✅ Programm startet....")
print(daten)
