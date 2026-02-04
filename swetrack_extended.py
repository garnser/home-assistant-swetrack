#!/usr/bin/env python3
"""
SweTrack: devices/info + device/info/extended (positions/voltage/temp/humidity)

pip install requests

config.json:
{
  "bearer_token": "XXXX"
}

Examples:
  python3 swetrack_extended.py
  python3 swetrack_extended.py --types position,voltage --hours 6
  python3 swetrack_extended.py --start 2026-02-04T00:00:00Z --stop 2026-02-04T23:59:59Z
  python3 swetrack_extended.py --pagesize 200 --max-rows 500 --dump-json out.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE_URL_DEFAULT = "https://api.cloudappapi.com/publicapi/v1"
DEVICES_INFO_PATH = "/devices/info"
DEVICE_EXTENDED_PATH = "/device/info/extended"


def _parse_iso(ts: str) -> datetime:
    # Accept "...Z" and offsets
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _to_iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def load_token(config_path: Path) -> str:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    token = data.get("bearer_token")
    if not token or not isinstance(token, str):
        raise ValueError(f'Missing/invalid "bearer_token" in {config_path}')
    return token.strip()


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_get(base_url: str, path: str, token: str, timeout: int) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    r = requests.get(url, headers=_headers(token), timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(base_url: str, path: str, token: str, body: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    r = requests.post(url, headers=_headers(token), json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_devices(base_url: str, token: str, timeout: int) -> List[Dict[str, Any]]:
    payload = api_get(base_url, DEVICES_INFO_PATH, token, timeout)
    if not payload.get("success"):
        raise RuntimeError(f"/devices/info error: {payload.get('error') or payload}")
    return payload.get("data", {}).get("devices", []) or []


def fetch_extended_all_pages(
    base_url: str,
    token: str,
    device_id: str,
    typ: str,
    start_iso: Optional[str],
    stop_iso: Optional[str],
    pagesize: int,
    max_rows: int,
    timeout: int,
) -> Tuple[List[Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns: (rows, meta)
    We keep it defensive because the exact 'data' structure differs by type.
    """
    all_rows: List[Any] = []
    page = 1
    last_meta: Dict[str, Any] = {}
    raw_pages: List[Dict[str, Any]] = []

    while True:
        body: Dict[str, Any] = {
            "deviceid": device_id,
            "type": typ,
            "page": page,
            "pagesize": pagesize,
        }
        # Docs mention time filters use startdatetime/stopdatetime (ISO 8601). :contentReference[oaicite:1]{index=1}
        if start_iso:
            body["startdatetime"] = start_iso
        if stop_iso:
            body["stopdatetime"] = stop_iso

        payload = api_post(base_url, DEVICE_EXTENDED_PATH, token, body, timeout)

        raw_pages.append(payload)

        if not payload.get("success"):
            raise RuntimeError(f"/device/info/extended error ({typ}): {payload.get('error') or payload}")

        data = payload.get("data", {}) or {}
        rows = []
        if isinstance(data, dict):
            if typ == "position":
                # Raw dump: positions are under data.positions :contentReference[oaicite:1]{index=1}
                rows = data.get("positions", [])
            elif typ == "voltage":
                # Raw dump: voltage is under data.voltage :contentReference[oaicite:2]{index=2}
                rows = data.get("voltage", [])
            else:
                # Keep fallback for future types (temp/humidity)
                rows = data.get(typ) or data.get(f"{typ}s") or []

        if rows is None:
            rows = []

        if not isinstance(rows, list):
            # If API returns an object, wrap it so caller still gets something
            rows = [rows]

        all_rows.extend(rows)
        last_meta = payload.get("meta", {}) or {}

        # Pagination object, if present
        pagination = payload.get("pagination") or payload.get("data", {}).get("pagination") or {}
        total_pages = pagination.get("total_pages")
        cur_page = pagination.get("page", page)

        if len(all_rows) >= max_rows:
            return all_rows[:max_rows], last_meta

        # Stop conditions
        if not rows:
            return all_rows, last_meta
        if isinstance(total_pages, int) and cur_page >= total_pages:
            return all_rows, last_meta, raw_pages

        page += 1


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return str(v)


def _pick_last_timestamp(row: Any) -> str:
    # Best-effort across potential schemas
    if isinstance(row, dict):
        for k in ("positiontime", "servertime", "datetime", "time", "timestamp"):
            if k in row and row[k]:
                return str(row[k])
    return "-"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json", help="Path to config.json (default: ./config.json)")
    ap.add_argument("--base-url", default=BASE_URL_DEFAULT, help=f"API base URL (default: {BASE_URL_DEFAULT})")
    ap.add_argument("--types", default="position,voltage,temp,humidity",
                    help="Comma-separated: position,voltage,temp,humidity (default: all)")
    ap.add_argument("--hours", type=int, default=24, help="Time window in hours back from now (default: 24)")
    ap.add_argument("--start", default=None, help="ISO 8601 startdatetime, e.g. 2026-02-04T00:00:00Z")
    ap.add_argument("--stop", default=None, help="ISO 8601 stopdatetime, e.g. 2026-02-04T23:59:59Z")
    ap.add_argument("--pagesize", type=int, default=200, help="Pagination pagesize (default: 200)")
    ap.add_argument("--max-rows", type=int, default=500, help="Max rows per (device,type) to fetch (default: 500)")
    ap.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds (default: 20)")
    ap.add_argument("--dump-json", default=None, help="Write full combined output to this JSON file")
    ap.add_argument("--dump-raw", default=None, help="Dump raw API responses (devices + extended) to this JSON file")
    args = ap.parse_args()

    token = load_token(Path(args.config))

    # Raw API capture (must be defined before first use)
    raw_api: Dict[str, Any] = {
        "devices_info": None,
        "device_info_extended": []
    }

    # Determine time window
    start_iso = args.start
    stop_iso = args.stop
    if not start_iso and not stop_iso:
        now = datetime.now(timezone.utc)
        start_iso = _to_iso_z(now - timedelta(hours=args.hours))
        stop_iso = _to_iso_z(now)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    devices_payload = api_get(args.base_url, DEVICES_INFO_PATH, token, args.timeout)
    if not devices_payload.get("success"):
        raise RuntimeError(f"/devices/info error: {devices_payload}")

    raw_api["devices_info"] = devices_payload
    devices = devices_payload.get("data", {}).get("devices", []) or []

    combined: Dict[str, Any] = {
        "generated_at": _to_iso_z(datetime.now(timezone.utc)),
        "window": {"startdatetime": start_iso, "stopdatetime": stop_iso},
        "devices": [],
    }

    for d in devices:
        dev_id = d.get("id")
        name = d.get("name", "-")
        model = (d.get("model") or {}).get("model", "-")
        status = d.get("status", "-")
        print(f"\n== {name} ({model}) id={dev_id} status={status} ==")

        dev_out: Dict[str, Any] = {
            "id": dev_id,
            "name": name,
            "model": model,
            "status": status,
            "extended": {},
        }

        for typ in types:
            try:
                rows, meta, raw_pages = fetch_extended_all_pages(
                    args.base_url,
                    token,
                    dev_id,
                    typ,
                    start_iso,
                    stop_iso,
                    args.pagesize,
                    args.max_rows,
                    args.timeout,
                )
            except Exception as e:
                print(f"  {typ:8}: ERROR: {e}")
                dev_out["extended"][typ] = {"error": str(e), "rows": []}
                continue

            dev_out["extended"][typ] = {"rows": rows, "meta": meta}
            raw_api["device_info_extended"].append({
                "device_id": dev_id,
                "device_name": name,
                "type": typ,
                "pages": raw_pages
            })

            # Print a tiny summary
            if rows:
                last = rows[-1]
                ts = _pick_last_timestamp(last)
                # Common “position” fields
                if isinstance(last, dict) and ("latitude" in last or "longitude" in last):
                    lat = last.get("latitude")
                    lon = last.get("longitude")
                    spd = last.get("speed", last.get("current_speed"))
                    if isinstance(spd, dict):
                        spd = spd.get("kmh", spd.get("mph", spd.get("knot")))
                    print(f"  {typ:8}: {len(rows):4} rows | last={ts} | lat={_fmt(lat)} lon={_fmt(lon)} speed={_fmt(spd)}")
                else:
                    # For voltage/temp/humidity etc.
                    # Try a few likely keys
                    val = None
                    if isinstance(last, dict):
                        for k in ("value", "voltage", "temp", "temperature", "humidity"):
                            if k in last:
                                val = last.get(k)
                                break
                    print(f"  {typ:8}: {len(rows):4} rows | last={ts} | value={_fmt(val)}")
            else:
                print(f"  {typ:8}:    0 rows (no data in window or unsupported on this device)")

        combined["devices"].append(dev_out)

    if args.dump_json:
        Path(args.dump_json).write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote: {args.dump_json}")

    if args.dump_raw:
        Path(args.dump_raw).write_text(
            json.dumps(raw_api, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"Wrote raw API dump: {args.dump_raw}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
