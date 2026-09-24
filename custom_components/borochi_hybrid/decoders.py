"""Dekodierfunktionen für die vom Borochi-Hybridwechselrichter gelesenen
Modbus-Register. Die Zuordnung wurde durch Scannen des Geräts und Abgleich
der Werte mit der Borochi-App ermittelt.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

Regs = dict[int, int | None]
Fn = Callable[[Regs], Any]


def scaled(address: int, scale: float = 1.0, signed: bool = False) -> Fn:
    """Ein 16-Bit-Register mit Faktor (optional vorzeichenbehaftet, S16)."""

    def fn(d: Regs) -> float | None:
        v = d.get(address)
        if v is None:
            return None
        if signed and v >= 0x8000:
            v -= 0x10000
        return round(v * scale, 4)

    return fn


def int32(address: int, scale: float = 1.0, signed: bool = True) -> Fn:
    """32-Bit-Register (High-Word zuerst), S32 standardmäßig vorzeichenbehaftet."""

    def fn(d: Regs) -> float | None:
        hi, lo = d.get(address), d.get(address + 1)
        if hi is None or lo is None:
            return None
        v = (hi << 16) | lo
        if signed and v >= 0x80000000:
            v -= 0x100000000
        return round(v * scale, 4)

    return fn


def pv_power(volt_addr: int, amp_addr: int) -> Fn:
    """PV-Leistung je String = Spannung (×0,1 V) × Strom (×0,01 A)."""

    def fn(d: Regs) -> float | None:
        u, i = d.get(volt_addr), d.get(amp_addr)
        if u is None or i is None:
            return None
        return round(u * 0.1 * i * 0.01, 1)

    return fn


def text(lo: int, hi: int) -> Callable[[Regs], str | None]:
    """ASCII-Text, 2 Zeichen pro Register (Ende exklusiv)."""

    def fn(d: Regs) -> str | None:
        chars: list[str] = []
        for a in range(lo, hi):
            v = d.get(a)
            if v is None:
                return None
            chars.append(chr(v >> 8) + chr(v & 0xFF))
        s = "".join(chars).replace("\x00", "").strip()
        return s if s and s.isprintable() else None

    return fn


def version(address: int) -> Callable[[Regs], str | None]:
    """Gepackte Version im Format x.x.xx:
    Bits 12-15 Hauptversion, Bits 8-11 Nebenversion, Bits 0-7 Revision.
    Beispiel: 0xAA14 -> V10.10.020.
    """

    def fn(d: Regs) -> str | None:
        v = d.get(address)
        if v is None:
            return None
        hi, lo = v >> 8, v & 0xFF
        return f"V{hi >> 4:02d}.{hi & 0xF:02d}.{lo:03d}"

    return fn


def version4(address: int) -> Callable[[Regs], str | None]:
    """Gepackte 4-teilige Version über 2 Register (x.x.x.x), je 1 Byte pro Zahl."""

    def fn(d: Regs) -> str | None:
        hi, lo = d.get(address), d.get(address + 1)
        if hi is None or lo is None:
            return None
        return f"V{hi >> 8}.{hi & 0xFF}.{lo >> 8}.{lo & 0xFF}"

    return fn


INVERTER_STATUS = {
    0: "Wartend",
    1: "Prüfung läuft",
    2: "Netzparallelbetrieb",
    3: "Notstromversorgung (EPS)",
    4: "Behebbarer Fehler",
    5: "Dauerhafter Fehler",
    6: "Aktualisierung läuft",
    7: "Eigenladung",
    8: "SVG",
    9: "PID",
}


def inverter_status(d: Regs) -> str | None:
    v = d.get(200)
    if v is None:
        return None
    return INVERTER_STATUS.get(v, f"Unbekannt ({v})")


WORKING_MODE = {
    0: "Eigenverbrauch",
    1: "Einspeisevorrang",
    2: "Bereitschaft (Backup)",
    3: "Inselbetrieb",
    4: "Benutzerdefiniert",
    5: "Debug",
    6: "ATE",
}


def working_mode(d: Regs) -> str | None:
    v = d.get(500)
    if v is None:
        return None
    return WORKING_MODE.get(v, f"Unbekannt ({v})")


def fault_status(d: Regs) -> str | None:
    """Sammelanzeige der Fehler-/Warncoderegister (279-290). Rohwerte, keine
    vollständige Dekodierung der einzelnen Bits."""
    codes = {a: d.get(a) for a in range(279, 291)}
    if any(v is None for v in codes.values()):
        return None
    active = {a: v for a, v in codes.items() if v}
    if not active:
        return "Kein Fehler/Warnung"
    parts = [f"Reg{a}=0x{v:04X}" for a, v in active.items()]
    return ", ".join(parts)


def cell_voltage_delta(d: Regs) -> float | None:
    mx, mn = d.get(564), d.get(565)
    if mx is None or mn is None:
        return None
    return round((mx - mn) * 0.001, 4)
