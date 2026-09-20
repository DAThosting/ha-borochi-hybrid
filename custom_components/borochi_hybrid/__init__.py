"""Borochi Hybrid Wechselrichter (Modbus RTU) - Beta."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BAUDRATE, CONF_PORT, CONF_SLAVE
from .coordinator import BorochiCoordinator
from .modbus_client import BorochiClient

PLATFORMS = [Platform.SENSOR]

type BorochiConfigEntry = ConfigEntry[BorochiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BorochiConfigEntry) -> bool:
    client = BorochiClient(
        entry.data[CONF_PORT], entry.data[CONF_SLAVE], entry.data[CONF_BAUDRATE]
    )
    coordinator = BorochiCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    return True


async def _reload_on_update(hass: HomeAssistant, entry: BorochiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BorochiConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.async_close()
    return unloaded
