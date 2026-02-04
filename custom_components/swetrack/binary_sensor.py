from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

BINS = [
    ("connectivity", "Connectivity", BinarySensorDeviceClass.CONNECTIVITY),
    ("external_power", "External power", BinarySensorDeviceClass.PLUG),
    ("ignition", "Ignition", None),  # no perfect built-in class
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for dev in coordinator.data["devices"]:
        for key, name, dev_class in BINS:
            entities.append(SweTrackBinarySensor(entry, coordinator, dev["id"], key, name, dev_class))
    async_add_entities(entities, True)

class SweTrackBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, coordinator, device_id, key, name, dev_class) -> None:
        self.entry = entry
        self.coordinator = coordinator
        self.device_id = device_id
        self.key = key
        self._attr_unique_id = f"{entry.entry_id}_{device_id}_{key}"
        self._attr_name = name
        self._attr_device_class = dev_class

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
    def is_on(self):
        dev = self._device()

        if self.key == "connectivity":
            # status: "offline" / presumably "online" :contentReference[oaicite:8]{index=8}
            return (dev.get("status") or "").lower() == "online"

        if self.key == "external_power":
            batt = dev.get("battery") or {}
            return bool(batt.get("external_power_supply"))

        if self.key == "ignition":
            ign = dev.get("ignition") or {}
            return bool(ign.get("value"))

        return None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
