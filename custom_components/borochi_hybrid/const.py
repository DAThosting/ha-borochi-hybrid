"""Konstanten der Borochi-Hybrid-Integration."""

DOMAIN = "borochi_hybrid"

CONF_PORT = "port"
CONF_SLAVE = "slave"
CONF_BAUDRATE = "baudrate"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GRID_INVERT = "grid_invert"

DEFAULT_PORT = "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
DEFAULT_SLAVE = 1
DEFAULT_BAUDRATE = 9600
DEFAULT_SCAN_INTERVAL = 30  # Sekunden

# Selten ändernde Werte (Gerätename, Firmware, Batteriekonfiguration) nur
# alle 10 Minuten lesen, um die langsame RS485-Verbindung zu entlasten.
SLOW_INTERVAL = 600

# Input-Register (Funktionscode 0x04), 0-basierte Protokolladressen.
# Durch Scannen des Geräts und Abgleich mit der Borochi-App ermittelt.
# Ende jeweils exklusiv.
FAST_BLOCKS: list[tuple[int, int]] = [
    (200, 291),  # Status, Temperaturen, PV, Netz, Fehler-/Warncodes
    (500, 575),  # Betriebsmodus, Energiezähler, EPS, Batterie, Hausverbrauch
    (700, 741),  # externer Zähler (Smart Meter)
]
SLOW_BLOCKS: list[tuple[int, int]] = [
    (0, 75),       # Modell, Seriennummer, Kennzahlen, Firmware
    (1900, 1924),  # Batterietyp, Zellenzahl, Kapazität, BMS-Version, Seriennr.
]
