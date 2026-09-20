"""Sensoren. Register mit '(experimentell)' sind noch nicht sicher zugeordnet."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BorochiConfigEntry
from .const import DOMAIN
from .coordinator import BorochiCoordinator
from .decoders import (
    cell_delta,
    cell_max,
    cell_min,
    pv_power,
    scaled,
    temp_max,
    temp_min,
    text,
    version,
)

V = UnitOfElectricPotential.VOLT
A = UnitOfElectricCurrent.AMPERE
MEAS = SensorStateClass.MEASUREMENT
DIAG = EntityCategory.DIAGNOSTIC


@dataclass(frozen=True, kw_only=True)
class BorochiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[int, int | None]], Any]


def _num(key, name, fn, unit, dc=None, prec=1, **kw) -> BorochiSensorDescription:
    return BorochiSensorDescription(
        key=key,
        name=name,
        value_fn=fn,
        native_unit_of_measurement=unit,
        device_class=dc,
        state_class=kw.pop("state_class", MEAS),
        suggested_display_precision=prec,
        **kw,
    )


def _exp(key, name, fn, unit, dc=None, prec=1) -> BorochiSensorDescription:
    """Experimentell: standardmäßig deaktiviert."""
    return _num(
        key, f"{name} (experimentell)", fn, unit, dc, prec,
        entity_registry_enabled_default=False,
    )


def _info(key, name, fn) -> BorochiSensorDescription:
    return BorochiSensorDescription(
        key=key, name=name, value_fn=fn, entity_category=DIAG
    )


VOLT_DC = SensorDeviceClass.VOLTAGE
CURR_DC = SensorDeviceClass.CURRENT
TEMP_DC = SensorDeviceClass.TEMPERATURE
C = UnitOfTemperature.CELSIUS

SENSORS: tuple[BorochiSensorDescription, ...] = (
    # ---- Netz ----
    _num("grid_voltage_l1", "Netzspannung L1", scaled(262, 0.1), V, VOLT_DC),
    _num("grid_voltage_l2", "Netzspannung L2", scaled(264, 0.1), V, VOLT_DC),
    _num("grid_voltage_l3", "Netzspannung L3", scaled(266, 0.1), V, VOLT_DC),
    _num("grid_current_l1", "Netzstrom L1", scaled(263, 0.1), A, CURR_DC),
    _num("grid_current_l2", "Netzstrom L2", scaled(265, 0.1), A, CURR_DC),
    _num("grid_current_l3", "Netzstrom L3", scaled(267, 0.1), A, CURR_DC),
    _num("grid_voltage_l12", "Netzspannung L1-L2", scaled(268, 0.1), V, VOLT_DC),
    _num("grid_voltage_l23", "Netzspannung L2-L3", scaled(269, 0.1), V, VOLT_DC),
    _num("grid_voltage_l31", "Netzspannung L3-L1", scaled(270, 0.1), V, VOLT_DC),
    _num("grid_frequency", "Netzfrequenz", scaled(271, 0.01),
         UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, 2),
    # ---- PV ----
    _num("pv1_voltage", "PV1 Spannung", scaled(208, 0.1), V, VOLT_DC),
    _num("pv2_voltage", "PV2 Spannung", scaled(206, 0.1), V, VOLT_DC),
    _exp("pv1_current", "PV1 Strom", scaled(223, 0.01), A, CURR_DC, 2),
    _exp("pv2_current", "PV2 Strom", scaled(225, 0.01), A, CURR_DC, 2),
    _exp("pv1_power", "PV1 Leistung", pv_power(208, 223), UnitOfPower.WATT,
         SensorDeviceClass.POWER, 0),
    _exp("pv2_power", "PV2 Leistung", pv_power(206, 225), UnitOfPower.WATT,
         SensorDeviceClass.POWER, 0),
    # ---- Batterie ----
    _num("battery_voltage", "Batteriespannung", scaled(529, 0.1), V, VOLT_DC),
    _num("battery_soc", "Batterie SOC", scaled(533, 0.1), PERCENTAGE,
         SensorDeviceClass.BATTERY),
    _num("battery_soh", "Batterie SOH", scaled(534, 0.1), PERCENTAGE, None,
         entity_category=DIAG),
    _num("battery_cycles", "Batterie Zyklen", scaled(535), None, None, 0,
         entity_category=DIAG),
    _num("battery_temperature", "Batterietemperatur", scaled(536, 0.1), C, TEMP_DC),
    _exp("bms_temperature", "BMS-Temperatur", scaled(538, 0.1), C, TEMP_DC),
    _exp("battery_current", "Batteriestrom", scaled(570, 0.01), A, CURR_DC, 2),
    _num("battery_capacity", "Batteriekapazität", scaled(1905, 0.1),
         UnitOfEnergy.KILO_WATT_HOUR, None, 1, state_class=None,
         entity_category=DIAG),
    # ---- Zellen (Auswertung von 128 Zellen) ----
    _num("cell_min", "Zellspannung min", cell_min,
         UnitOfElectricPotential.MILLIVOLT, VOLT_DC, 0),
    _num("cell_max", "Zellspannung max", cell_max,
         UnitOfElectricPotential.MILLIVOLT, VOLT_DC, 0),
    _num("cell_delta", "Zellspannung Spreizung", cell_delta,
         UnitOfElectricPotential.MILLIVOLT, VOLT_DC, 0),
    _num("cell_temp_min", "Zelltemperatur min", temp_min, C, TEMP_DC),
    _num("cell_temp_max", "Zelltemperatur max", temp_max, C, TEMP_DC),
    # ---- Geräteinfo ----
    _info("model", "Modell", text(0, 6)),
    _info("serial", "Seriennummer", text(16, 24)),
    _info("fw_main_arm", "Firmware Haupt-ARM", version(66)),
    _info("fw_aux_arm", "Firmware Hilfs-ARM", version(68)),
    _info("fw_main_dsp", "Firmware Haupt-DSP", version(70)),
    _num("rated_power", "Nennleistung", scaled(61), UnitOfPower.WATT, None, 0,
         state_class=None, entity_category=DIAG),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: BorochiConfigEntry, add: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    add(BorochiSensor(coordinator, entry, d) for d in SENSORS)


class BorochiSensor(CoordinatorEntity[BorochiCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: BorochiSensorDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{self._uid}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        d = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._uid)},
            manufacturer="Borochi",
            name="Borochi Hybridwechselrichter",
            model=text(0, 6)(d),
            serial_number=text(16, 24)(d),
            sw_version=version(66)(d),
        )

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data or {})
