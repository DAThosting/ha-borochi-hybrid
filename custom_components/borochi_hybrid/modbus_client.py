"""Schlanker, nur lesender Modbus-RTU-Client für den Borochi-Wechselrichter."""
from __future__ import annotations

import asyncio
import logging

from pymodbus.client import AsyncModbusSerialClient

from .decoders import Regs, text

_LOGGER = logging.getLogger(__name__)
PAUSE = 0.05  # Pause zwischen Anfragen, das Gerät antwortet träge


class BorochiClient:
    """Liest Input-Register (Funktionscode 0x04). Schreibt niemals."""

    def __init__(self, port: str, slave: int, baudrate: int) -> None:
        self._port = port
        self._slave = slave
        self._baudrate = baudrate
        self._client: AsyncModbusSerialClient | None = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> bool:
        if self._client is None:
            self._client = AsyncModbusSerialClient(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=2,
                retries=1,
            )
        if self._client.connected:
            return True
        try:
            return bool(await self._client.connect())
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Verbindung zu %s fehlgeschlagen: %s", self._port, err)
            return False

    async def _read(self, address: int, count: int) -> list[int] | None:
        assert self._client is not None
        try:
            try:
                rr = await self._client.read_input_registers(
                    address, count=count, device_id=self._slave
                )
            except TypeError:  # ältere pymodbus-Versionen
                rr = await self._client.read_input_registers(
                    address, count=count, slave=self._slave
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Lesefehler Register %s (+%s): %s", address, count, err)
            return None
        if rr.isError():
            return None
        return list(rr.registers)

    async def read_range(self, lo: int, hi: int, step: int = 5) -> Regs:
        """Liest [lo, hi) in kleinen Blöcken; bei Fehler einzeln nachlesen."""
        result: Regs = {}
        async with self._lock:
            if not await self._ensure():
                return {a: None for a in range(lo, hi)}
            for start in range(lo, hi, step):
                n = min(step, hi - start)
                regs = await self._read(start, n)
                if regs is None or len(regs) != n:
                    regs = []
                    for a in range(start, start + n):
                        one = await self._read(a, 1)
                        regs.append(one[0] if one else None)
                        await asyncio.sleep(PAUSE)
                for i, v in enumerate(regs):
                    result[start + i] = v
                await asyncio.sleep(PAUSE)
        return result

    async def async_probe(self) -> dict[str, str] | None:
        """Prüft die Verbindung und liefert Modell und Seriennummer."""
        model = text(0, 6)(await self.read_range(0, 6))
        serial = text(16, 24)(await self.read_range(16, 24))
        if model is None:
            return None
        return {"model": model, "serial": serial or f"{self._port}_{self._slave}"}

    async def async_close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
