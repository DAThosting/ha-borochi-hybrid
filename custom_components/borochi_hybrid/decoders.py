"""Hilfsfunktionen zum Dekodieren der Rohregister (reine Python-Funktionen)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

Regs = dict[int, int | None]
Fn = Callable[[Regs], Any]


def scaled(address: int, scale: float = 1.0, signed: bool = False) -> Fn:
    """Ein 16-Bit-Register mit Faktor (optional vorzeichenbehaftet)."""

    def fn(d: Regs) -> float | None:
        v = d.get(address)
        if v is None:
            return None
        if signed and v >= 0x8000:
            v -= 0x10000
        return round(v * scale, 4)

    return fn


def int32(address: int, scale: float = 1.0) -> Callable[[Regs], float | None]:
    """32-Bit vorzeichenbehaftet, High-Word zuerst."""

    def fn(d: Regs) -> float | None:
        hi, lo = d.get(address), d.get(address + 1)
        if hi is None or lo is None:
            return None
        v = (hi << 16) | lo
        if v >= 0x80000000:
            v -= 0x100000000
        return round(v * scale, 4)

    return fn


def pv_total(pairs: tuple[tuple[int, int], ...]) -> Callable[[Regs], float | None]:
    """Summe der PV-Leistungen aus (Spannungs-, Strom-)Registerpaaren."""

    def fn(d: Regs) -> float | None:
        total = 0.0
        for ua, ia in pairs:
            u, i = d.get(ua), d.get(ia)
            if u is None or i is None:
                return None
            total += u * 0.1 * i * 0.01
        return round(total, 1)

    return fn


def pv_sum(a: int, b: int) -> Callable[[Regs], float | None]:
    """Summe zweier Leistungsregister (W)."""

    def fn(d: Regs) -> float | None:
        x, y = d.get(a), d.get(b)
        return None if x is None or y is None else float(x + y)

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
    """Gepackte Version, z. B. 43540 (0xAA14) -> V10.10.020."""

    def fn(d: Regs) -> str | None:
        v = d.get(address)
        if v is None:
            return None
        hi, lo = v >> 8, v & 0xFF
        return f"V{hi >> 4:02d}.{hi & 0xF:02d}.{lo:03d}"

    return fn


def pv_power(volt_addr: int, amp_addr: int) -> Callable[[Regs], float | None]:
    """PV-Leistung = Spannung (0,1 V) x Strom (0,01 A)."""

    def fn(d: Regs) -> float | None:
        u, i = d.get(volt_addr), d.get(amp_addr)
        if u is None or i is None:
            return None
        return round(u * 0.1 * i * 0.01, 1)

    return fn


def cell_voltages(d: Regs) -> list[int]:
    """Plausible Zellspannungen in mV (Register 2300-2427)."""
    vals = [d.get(a) for a in range(2300, 2428)]
    return [v for v in vals if v is not None and 2000 <= v <= 4500]


def cell_temps(d: Regs) -> list[float]:
    """Temperaturfühler in °C (Register 2428-2445, Faktor 0,1)."""
    vals = [d.get(a) for a in range(2428, 2446)]
    return [v / 10 for v in vals if v]


def cell_min(d: Regs) -> int | None:
    c = cell_voltages(d)
    return min(c) if c else None


def cell_max(d: Regs) -> int | None:
    c = cell_voltages(d)
    return max(c) if c else None


def cell_delta(d: Regs) -> int | None:
    c = cell_voltages(d)
    return max(c) - min(c) if c else None


def temp_min(d: Regs) -> float | None:
    t = cell_temps(d)
    return min(t) if t else None


def temp_max(d: Regs) -> float | None:
    t = cell_temps(d)
    return max(t) if t else None
