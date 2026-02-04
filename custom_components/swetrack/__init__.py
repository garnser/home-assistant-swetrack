from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import SweTrackApiClient
from .const import (
    CONF_BASE_URL,
    CONF_FETCH_EXTENDED,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_FETCH_EXTENDED,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SweTrackCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    token = entry.data[CONF_TOKEN]
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    fetch_extended = entry.options.get(CONF_FETCH_EXTENDED, DEFAULT_FETCH_EXTENDED)

    api = SweTrackApiClient(hass, token=token, base_url=base_url)
    coordinator = SweTrackCoordinator(hass, api=api, scan_interval_s=scan_interval, fetch_extended=fetch_extended)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
