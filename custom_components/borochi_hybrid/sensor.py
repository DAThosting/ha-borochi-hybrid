"""Sensoren für den Borochi-Hybridwechselrichter (Input-Register,
Funktionscode 0x04). Register mit '(experimentell)' sind noch nicht mit
Messwerten gegengeprüft oder ihre genaue Bedeutung ist unklar.
"""
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
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BorochiConfigEntry
from .const import CONF_GRID_INVERT, DOMAIN
from .coordinator import BorochiCoordinator
from .decoders import (
    cell_voltage_delta,
    fault_status,
    int32,
    inverter_status,
    pv_power,
    scaled,
    text,
    version,
    version4,
    working_mode,
)

V = UnitOfElectricPotential.VOLT
A = UnitOfElectricCurrent.AMPERE
W = UnitOfPower.WATT
KWH = UnitOfEnergy.KILO_WATT_HOUR
C = UnitOfTemperature.CELSIUS
MEAS = SensorStateClass.MEASUREMENT
TOTAL_INC = SensorStateClass.TOTAL_INCREASING
DIAG = EntityCategory.DIAGNOSTIC

VOLT_DC = SensorDeviceClass.VOLTAGE
CURR_DC = SensorDeviceClass.CURRENT
POWER_DC = SensorDeviceClass.POWER
ENERGY_DC = SensorDeviceClass.ENERGY
TEMP_DC = SensorDeviceClass.TEMPERATURE
FREQ_DC = SensorDeviceClass.FREQUENCY


@dataclass(frozen=True, kw_only=True)
class BorochiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[int, int | None]], Any]
    grid_kind: str | None = None  # power | import | export


def _num(key, name, fn, unit=None, dc=None, prec=1, **kw) -> BorochiSensorDescription:
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


def _energy(key, name, fn, prec=1, **kw) -> BorochiSensorDescription:
    return _num(key, name, fn, KWH, ENERGY_DC, prec, state_class=TOTAL_INC, **kw)


def _exp(key, name, fn, unit=None, dc=None, prec=1, **kw) -> BorochiSensorDescription:
    """Experimentell: Bedeutung/Faktor unklar oder unbestätigt; standardmäßig aus."""
    return _num(
        key, f"{name} (experimentell)", fn, unit, dc, prec,
        entity_registry_enabled_default=False, **kw,
    )


def _info(key, name, fn) -> BorochiSensorDescription:
    return BorochiSensorDescription(
        key=key, name=name, value_fn=fn, entity_category=DIAG
    )


def _grid(key, name, kind) -> BorochiSensorDescription:
    # Quelle: Register 274/275 (S32, ×1 W).
    # Positiv = Netzbezug, negativ = Einspeisung - entspricht bereits
    # der Home-Assistant-Konvention.
    return BorochiSensorDescription(
        key=key,
        name=name,
        value_fn=int32(274),
        grid_kind=kind,
        native_unit_of_measurement=W,
        device_class=POWER_DC,
        state_class=MEAS,
        suggested_display_precision=0,
    )


SENSORS: tuple[BorochiSensorDescription, ...] = (
    # ================= Gerätestatus / Betriebsmodus =================
    _info("inverter_status", "Wechselrichter-Status", inverter_status),
    _info("working_mode", "Betriebsmodus", working_mode),
    _info("fault_status", "Fehler-/Warnstatus", fault_status),
    # ================= PV =================
    _num("pv_total_power", "PV Gesamtleistung", int32(220, signed=False), W,
         POWER_DC, 0),
    _num("pv1_voltage", "PV1 Spannung", scaled(222, 0.1), V, VOLT_DC),
    _num("pv1_current", "PV1 Strom", scaled(223, 0.01), A, CURR_DC, 2),
    _num("pv1_power", "PV1 Leistung", pv_power(222, 223), W, POWER_DC, 0),
    _num("pv2_voltage", "PV2 Spannung", scaled(224, 0.1), V, VOLT_DC),
    _num("pv2_current", "PV2 Strom", scaled(225, 0.01), A, CURR_DC, 2),
    _num("pv2_power", "PV2 Leistung", pv_power(224, 225), W, POWER_DC, 0),
    _energy("pv_daily_energy", "PV Ertrag heute", int32(501, 0.1, False)),
    _energy("pv_total_energy", "PV Ertrag gesamt", int32(503, 0.1, False)),
    # ================= Netz (am Wechselrichter-Anschluss) =================
    # positiv = Netzbezug, negativ = Einspeisung (siehe _grid oben)
    _grid("grid_power", "Netzleistung", "power"),
    _grid("grid_export", "Einspeisung", "export"),
    _grid("grid_import", "Netzbezug", "import"),
    _num("grid_voltage_l1", "Netzspannung L1", scaled(262, 0.1), V, VOLT_DC),
    _num("grid_voltage_l2", "Netzspannung L2", scaled(264, 0.1), V, VOLT_DC),
    _num("grid_voltage_l3", "Netzspannung L3", scaled(266, 0.1), V, VOLT_DC),
    _num("grid_current_l1", "Netzstrom L1", scaled(263, 0.1, True), A, CURR_DC, 1),
    _num("grid_current_l2", "Netzstrom L2", scaled(265, 0.1, True), A, CURR_DC, 1),
    _num("grid_current_l3", "Netzstrom L3", scaled(267, 0.1, True), A, CURR_DC, 1),
    _num("grid_voltage_l12", "Netzspannung L1-L2", scaled(268, 0.1), V, VOLT_DC),
    _num("grid_voltage_l23", "Netzspannung L2-L3", scaled(269, 0.1), V, VOLT_DC),
    _num("grid_voltage_l31", "Netzspannung L3-L1", scaled(270, 0.1), V, VOLT_DC),
    _num("grid_frequency", "Netzfrequenz", scaled(271, 0.01),
         UnitOfFrequency.HERTZ, FREQ_DC, 2),
    _num("grid_reactive_power", "Netz Blindleistung", int32(272), None, None, 0,
         native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
         entity_category=DIAG),
    _num("grid_apparent_power", "Netz Scheinleistung", int32(276, 1, False),
         UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, 0,
         entity_category=DIAG),
    _num("grid_power_factor", "Netz Leistungsfaktor", scaled(278, 0.01, True),
         None, SensorDeviceClass.POWER_FACTOR, 2, entity_category=DIAG),
    _energy("grid_daily_import_energy", "Netzbezug Energie heute", int32(505, 0.1, False)),
    _energy("grid_total_import_energy", "Netzbezug Energie gesamt", int32(507, 0.1, False)),
    # Externer Zähler (Smart Meter): eigene, meist genauere Energiezähler
    _energy("meter_import_energy", "Netzbezug Energie (Zähler)", int32(729, 0.01, False), 2),
    _energy("meter_export_energy", "Einspeisung Energie (Zähler)", int32(731, 0.01, False), 2),
    # ================= Haus =================
    _num("house_power", "Hausverbrauch", int32(569, 1, False), W, POWER_DC, 0),
    _energy("house_daily_energy", "Hausverbrauch Energie heute", int32(571, 0.1, False)),
    _energy("house_total_energy", "Hausverbrauch Energie gesamt", int32(573, 0.1, False)),
    # ================= Batterie =================
    _num("battery_voltage", "Batteriespannung", scaled(529, 0.1), V, VOLT_DC),
    _num("battery_current", "Batteriestrom", scaled(530, 0.1, True), A, CURR_DC, 1),
    _num("battery_power", "Batterieleistung", int32(531), W, POWER_DC, 0),
    _num("battery_soc", "Batterie SOC", scaled(533, 0.1), PERCENTAGE,
         SensorDeviceClass.BATTERY),
    _num("battery_soh", "Batterie SOH", scaled(534, 0.1), PERCENTAGE, None,
         entity_category=DIAG),
    _num("battery_cycles", "Batterie Zyklen", scaled(535), None, None, 0,
         entity_category=DIAG),
    _num("battery_temperature", "Batterietemperatur", scaled(536, 0.1, True), C, TEMP_DC),
    _num("bms_temperature", "BMS-Temperatur", scaled(538, 0.1, True), C, TEMP_DC,
         entity_category=DIAG),
    _num("battery_cell_max_voltage", "Zellspannung max", scaled(564, 0.001), V,
         VOLT_DC, 3),
    _num("battery_cell_min_voltage", "Zellspannung min", scaled(565, 0.001), V,
         VOLT_DC, 3),
    _num("battery_cell_voltage_delta", "Zellspannung Spreizung",
         cell_voltage_delta, V, VOLT_DC, 3),
    _energy("battery_daily_charge_energy", "Batterie Ladeenergie heute", int32(544, 0.1, False)),
    _energy("battery_daily_discharge_energy", "Batterie Entladeenergie heute", int32(546, 0.1, False)),
    _energy("battery_total_charge_energy", "Batterie Ladeenergie gesamt", int32(548, 0.1, False)),
    _energy("battery_total_discharge_energy", "Batterie Entladeenergie gesamt", int32(550, 0.1, False)),
    _num("battery_capacity", "Batteriekapazität", scaled(1905, 0.1), KWH, None, 1,
         state_class=None, entity_category=DIAG),
    _info("battery_serial", "Batterie Seriennummer", text(1908, 1924)),
    _info("bms_version", "BMS Software-Version", version4(1906)),
    # ================= Wechselrichter (Diagnose) =================
    _num("inverter_temperature", "Wechselrichter-Temperatur", scaled(210, 0.1, True),
         C, TEMP_DC, entity_category=DIAG),
    _num("ambient_temperature", "Umgebungstemperatur", scaled(211, 0.1, True), C,
         TEMP_DC, entity_category=DIAG),
    _num("bus_voltage", "Zwischenkreisspannung", scaled(215, 0.1), V, VOLT_DC,
         entity_category=DIAG),
    _energy("inverter_daily_energy", "Wechselrichter Energie heute (AC)",
            int32(203, 0.1, False), entity_category=DIAG),
    _energy("inverter_total_energy", "Wechselrichter Energie gesamt (AC)",
            int32(205, 0.1, False), entity_category=DIAG),
    _num("running_time", "Laufzeit gesamt", int32(207, 1, False),
         UnitOfTime.MINUTES, SensorDeviceClass.DURATION, 0, state_class=TOTAL_INC,
         entity_category=DIAG),
    # ================= Geräteinfo =================
    _info("model", "Modell", text(0, 16)),
    _info("serial", "Seriennummer", text(16, 32)),
    _num("rated_power", "Nennleistung", int32(60, 1, False), W, None, 0,
         state_class=None, entity_category=DIAG),
    _num("modbus_address", "Modbus-Adresse", scaled(63), None, None, 0,
         state_class=None, entity_category=DIAG),
    _info("hw_version", "Hardware-Version", version(64)),
    _info("fw_main_arm", "Firmware Haupt-ARM", version(66)),
    _info("fw_aux_arm", "Firmware Hilfs-ARM", version(68)),
    _info("fw_main_dsp", "Firmware Haupt-DSP", version(70)),
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
        self._invert = entry.options.get(CONF_GRID_INVERT, False)

    @property
    def device_info(self) -> DeviceInfo:
        d = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._uid)},
            manufacturer="Borochi",
            name="Borochi Hybridwechselrichter",
            model=text(0, 16)(d),
            serial_number=text(16, 32)(d),
            sw_version=version(66)(d),
        )

    @property
    def native_value(self):
        value = self.entity_description.value_fn(self.coordinator.data or {})
        kind = self.entity_description.grid_kind
        if kind is None or value is None:
            return value
        if self._invert:
            value = -value
        if kind == "import":
            return max(value, 0)
        if kind == "export":
            return max(-value, 0)
        return value
