from __future__ import annotations

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SweTrackDeviceTracker(entry, coordinator, dev) for dev in coordinator.data["devices"]], True)

class SweTrackDeviceTracker(TrackerEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator, device: dict) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self.device_id = device["id"]
        self._attr_unique_id = f"{entry.entry_id}_{self.device_id}_tracker"
        self._attr_name = device.get("name") or self.device_id

    @property
    def device_info(self):
        # one HA Device per SweTrack device
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
    def latitude(self):
        pos = (self._device().get("position_info") or {})
        return pos.get("latitude")

    @property
    def longitude(self):
        pos = (self._device().get("position_info") or {})
        return pos.get("longitude")

    @property
    def source_type(self):
        return "gps"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def extra_state_attributes(self):
        dev = self._device()
        pos = dev.get("position_info") or {}
        ext = (self.coordinator.data.get("extended") or {}).get(self.device_id, {})
        latest_pos = ext.get("position_latest")
        return {
            "swetrack_id": self.device_id,
            "last_update": dev.get("last_update"),
            "position_time": (latest_pos or {}).get("positiontime") or pos.get("datetime"),
        }
