from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SweTrackApiClient, SweTrackApiError
from .const import DOMAIN

def _extract_extended_rows(payload: dict[str, Any], typ: str) -> list[dict[str, Any]]:
    data = (payload.get("data") or {})
    if not isinstance(data, dict):
        return []
    if typ == "position":
        # schema: data.positions :contentReference[oaicite:4]{index=4}
        rows = data.get("positions", [])
    elif typ == "voltage":
        # schema: data.voltage :contentReference[oaicite:5]{index=5}
        rows = data.get("voltage", [])
    else:
        rows = data.get(typ) or data.get(f"{typ}s") or []
    return rows if isinstance(rows, list) else []

class SweTrackCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: SweTrackApiClient, scan_interval_s: int, fetch_extended: bool) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_s),
        )
        self.api = api
        self.fetch_extended = fetch_extended

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            devices_payload = await self.api.async_get_devices()
            devices = (devices_payload.get("data") or {}).get("devices") or []
            if not isinstance(devices, list):
                devices = []

            extended_by_device: dict[str, dict[str, Any]] = {}

            if self.fetch_extended:
                # Per-device “latest” samples (pagesize=1)
                for d in devices:
                    device_id = d.get("id")
                    if not device_id:
                        continue

                    ext: dict[str, Any] = {}

                    # position latest
                    pos_payload = await self.api.async_get_extended(device_id, "position", pagesize=1)
                    pos_rows = _extract_extended_rows(pos_payload, "position")
                    if pos_rows:
                        ext["position_latest"] = pos_rows[0]

                    # voltage latest
                    volt_payload = await self.api.async_get_extended(device_id, "voltage", pagesize=1)
                    volt_rows = _extract_extended_rows(volt_payload, "voltage")
                    if volt_rows:
                        ext["voltage_latest"] = volt_rows[0]

                    extended_by_device[device_id] = ext

            return {
                "devices_payload": devices_payload,
                "devices": devices,
                "extended": extended_by_device,
            }

        except SweTrackApiError as e:
            raise UpdateFailed(str(e)) from e
        except Exception as e:
            raise UpdateFailed(f"Unexpected error: {e}") from e
