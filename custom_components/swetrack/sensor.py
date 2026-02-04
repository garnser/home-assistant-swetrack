from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfSpeed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SENSORS = [
    ("battery_internal", "Battery", SensorDeviceClass.BATTERY, PERCENTAGE),
    ("external_voltage", "External voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT),
    ("speed_current", "Speed", SensorDeviceClass.SPEED, UnitOfSpeed.KILOMETERS_PER_HOUR),
    ("speed_limit", "Speed limit", SensorDeviceClass.SPEED, UnitOfSpeed.KILOMETERS_PER_HOUR),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for dev in coordinator.data["devices"]:
        for key, name, dev_class, unit in SENSORS:
            entities.append(SweTrackSensor(entry, coordinator, dev["id"], dev.get("name") or dev["id"], key, name, dev_class, unit))
    async_add_entities(entities, True)

class SweTrackSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, coordinator, device_id, device_name, key, name, device_class, unit) -> None:
        self.entry = entry
        self.coordinator = coordinator
        self.device_id = device_id
        self.key = key
        self._attr_unique_id = f"{entry.entry_id}_{device_id}_{key}"
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def device_info(self):
        dev = self._device()
        model = (dev.get("model") or {}).get("model")
        uniqueid = dev.get("uniqueid")
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": dev.get("name") or self.device_id,
            "manufacturer": "SweTrack",
            "model": model,
            "serial_number": uniqueid,
        }

    def _device(self) -> dict:
        for d in self.coordinator.data["devices"]:
            if d.get("id") == self.device_id:
                return d
        return {}

    @property
    def native_value(self):
        dev = self._device()
        batt = dev.get("battery") or {}
        spd = dev.get("speed") or {}

        if self.key == "battery_internal":
            return batt.get("internal")
        if self.key == "external_voltage":
            # Prefer latest extended voltage sample if enabled :contentReference[oaicite:7]{index=7}
            ext = (self.coordinator.data.get("extended") or {}).get(self.device_id, {})
            v_latest = (ext.get("voltage_latest") or {}).get("value")
            return v_latest if v_latest is not None else batt.get("external_voltage")
        if self.key == "speed_current":
            return (spd.get("current_speed") or {}).get("value")
        if self.key == "speed_limit":
            return (spd.get("speed_limit") or {}).get("value")

        return None

    @property
    def extra_state_attributes(self):
        dev = self._device()
        ext = (self.coordinator.data.get("extended") or {}).get(self.device_id, {})
        v_latest = ext.get("voltage_latest") or {}
        return {
            "swetrack_id": self.device_id,
            "last_update": dev.get("last_update"),
            "voltage_servertime": v_latest.get("servertime"),
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
