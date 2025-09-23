# String-Eingabe
name = input("Bitte gib einen Text ein: ")

# Ganzzahl (Dezimalzahl ohne Komma)
zahl_int = int(input("Bitte gib eine ganze Zahl ein: "))

# Kommazahl (float in Python, Dezimaltrennzeichen ist der Punkt!)
#zahl_float = float(input("Bitte gib eine Kommazahl ein (z. B. 3.14): "))
zahl_float = float(input("Kommazahl (z. B. 3,14): ").replace(",", "."))

print("\n--- Deine Eingaben ---")
print(f"Text: {name}")
print(f"Ganze Zahl: {zahl_int}")
print(f"Kommazahl: {zahl_float}")
