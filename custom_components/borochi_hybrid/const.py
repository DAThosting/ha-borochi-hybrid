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

# Selten ändernde Werte (Zellen, Versionen, Seriennummer) nur alle 10 Minuten
SLOW_INTERVAL = 600

# Input-Register (0-basierte Protokolladressen), Ende exklusiv.
# Nur kleine Blöcke lesen: das Gerät ist bei 9600 Baud empfindlich.
FAST_BLOCKS: list[tuple[int, int]] = [
    (221, 226),  # PV: Gesamtleistung, U1, I1, U2, I2
    (262, 278),  # Netz + Leistungs-Kandidaten 272-277
    (529, 539),  # Batterie
    (570, 571),  # Hausverbrauch (Kandidat)
    (725, 727),  # Netzleistung gesamt (32 Bit, Kandidat)
]
SLOW_BLOCKS: list[tuple[int, int]] = [
    (0, 6),       # Modell
    (16, 24),     # Seriennummer
    (61, 62),     # Nennleistung
    (66, 71),     # Firmware-Versionen
    (1905, 1906),  # Batteriekapazität
    (2300, 2446),  # Zellspannungen + Temperaturen
]
