"""DataUpdateCoordinator für den Borochi-Wechselrichter."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAST_BLOCKS,
    SLOW_BLOCKS,
    SLOW_INTERVAL,
)
from .decoders import Regs
from .modbus_client import BorochiClient

_LOGGER = logging.getLogger(__name__)


class BorochiCoordinator(DataUpdateCoordinator[Regs]):
    """Holt Rohregister; die Dekodierung passiert in den Sensoren."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: BorochiClient
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self._slow: Regs = {}
        self._slow_ts = 0.0

    async def _async_update_data(self) -> Regs:
        fast: Regs = {}
        for lo, hi in FAST_BLOCKS:
            fast.update(await self.client.read_range(lo, hi))
        if not any(v is not None for v in fast.values()):
            raise UpdateFailed("Keine Antwort vom Wechselrichter (Port, Adresse, A/B?)")

        now = time.monotonic()
        if not self._slow or now - self._slow_ts > SLOW_INTERVAL:
            for lo, hi in SLOW_BLOCKS:
                block = await self.client.read_range(lo, hi, step=16)
                self._slow.update({a: v for a, v in block.items() if v is not None})
            self._slow_ts = now
        return {**self._slow, **fast}
