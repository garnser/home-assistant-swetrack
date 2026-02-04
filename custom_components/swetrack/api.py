from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

@dataclass
class SweTrackApiError(Exception):
    message: str

class SweTrackApiClient:
    def __init__(self, hass, token: str, base_url: str) -> None:
        self._hass = hass
        self._token = token
        self._base = base_url.rstrip("/")
        self._session = async_get_clientsession(hass)

    @property
    def base_url(self) -> str:
        return self._base

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base}{path}"
        async with self._session.request(method, url, headers=self._headers(), json=json_data) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400:
                raise SweTrackApiError(f"HTTP {resp.status}: {data}")
            if isinstance(data, dict) and data.get("success") is False:
                raise SweTrackApiError(f"API error: {data.get('error') or data}")
            if not isinstance(data, dict):
                raise SweTrackApiError(f"Unexpected response: {data}")
            return data

    async def async_get_devices(self) -> dict[str, Any]:
        # GET /devices/info
        return await self._request("GET", "/devices/info")

    async def async_get_account_info(self) -> dict[str, Any]:
        # GET /account/info (used for unique_id)
        return await self._request("GET", "/account/info")

    async def async_get_extended(self, device_id: str, typ: str, page: int = 1, pagesize: int = 1) -> dict[str, Any]:
        # POST /device/info/extended
        # Using pagesize=1 to fetch “latest” row assuming API returns newest first (as in your dump). :contentReference[oaicite:1]{index=1}
        body = {
            "deviceid": device_id,
            "type": typ,
            "page": page,
            "pagesize": pagesize,
        }
        return await self._request("POST", "/device/info/extended", json_data=body)
