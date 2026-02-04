# SweTrack Home Assistant (HACS) Integration

Custom Home Assistant integration for **SweTrack GPS trackers** using the SweTrack Tracking REST API.

* ✅ **Config Flow** setup (no YAML required)
* ✅ **One Home Assistant Device per SweTrack device**
* ✅ Entities for **location, battery, voltage, speed, ignition, connectivity**
* ✅ Optional polling of **extended telemetry** via `/device/info/extended`

> **Status:** early / preview (v0.1.0)

---

## Features

### Device model

Each SweTrack tracker becomes a **separate Home Assistant Device**, identified by its SweTrack device id.

### Entities created per device

Depending on what the API returns for the device model:

**Device Tracker**

* `device_tracker.<name>`

  * GPS coordinates from `position_info.latitude` / `position_info.longitude`

**Sensors**

* Battery (%) — `SensorDeviceClass.BATTERY`
* External voltage (V) — `SensorDeviceClass.VOLTAGE`
* Current speed (km/h) — `SensorDeviceClass.SPEED`
* Speed limit (km/h) — `SensorDeviceClass.SPEED`

**Binary Sensors**

* Connectivity (online/offline) — `BinarySensorDeviceClass.CONNECTIVITY`
* External power supply — `BinarySensorDeviceClass.PLUG`
* Ignition — (no built-in device class; still exposed)

### Extended telemetry (optional)

If enabled in **Options**, the integration will query:

* `POST /device/info/extended` with `type=position` (latest row)
* `POST /device/info/extended` with `type=voltage` (latest row)

This is mainly used to:

* expose `voltage` from the extended endpoint if present
* add timestamp attributes such as `positiontime` / `servertime`

> Note: Extended telemetry increases API calls (per-device). If you have many devices or a strict daily quota, disable it.

---

## Requirements

* Home Assistant 2023.6+ (config flows + coordinator pattern)
* A SweTrack account with an **External API Bearer token**

---

## Installation (HACS)

1. In your repository, ensure the integration lives at:

   ```
   custom_components/swetrack/
   ```

2. In HACS:

   * **HACS → Integrations → ⋮ → Custom repositories**
   * Add your Git repo URL
   * Category: **Integration**

3. Install **SweTrack** from HACS.

4. Restart Home Assistant.

---

## Setup (Config Flow)

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **SweTrack**
4. Enter:

   * **Bearer token** (required)
   * **Base URL** (optional; default is `https://api.cloudappapi.com/publicapi/v1`)

The integration validates the token by calling `/devices/info`.

---

## Options

After installation:

1. **Settings → Devices & Services → SweTrack → Options**
2. Configure:

   * **Scan interval (seconds)** — default `300` (5 minutes)
   * **Fetch extended telemetry** — default `true`

### API usage guidance

* `/devices/info` is one call per refresh.
* Extended telemetry adds **2 calls per device** per refresh (position + voltage).

If you have many devices, prefer:

* larger scan interval, or
* disable extended telemetry.

---

## Entities and Attributes

### Common attributes

Most entities include:

* `swetrack_id`
* `last_update` (from `/devices/info`)

Extended-enabled entities may also include:

* `position_time` (from `positiontime`)
* `voltage_servertime` (from `servertime`)

---

## Troubleshooting

### Authentication failed

* Confirm you pasted the token correctly
* Remember: SweTrack may only allow **one active external token** per account; refreshing/rotating it can invalidate the previous token.

### No location updates

* The device may be offline
* The device may not have reported a new position recently

### No voltage/telemetry rows

* Extended telemetry depends on device capabilities and data availability.
* Try increasing scan interval and/or verify the device is reporting.

---

## Development

### Run style checks (optional)

This skeleton keeps dependencies minimal. If you want linting:

* `ruff`
* `black`

### Useful Home Assistant docs

* DataUpdateCoordinator pattern
* Config Flow pattern

---

## Roadmap / Ideas

* Switch entities for **relay** and **power-saving mode** using `/device/edit`
* Webhook receiver mode (if SweTrack enables push for your account)
* History sensors (e.g., last trip distance, max speed in 24h)

---

## License

Choose a license for your repository (MIT is common for HACS projects).

---

## Disclaimer

This project is not affiliated with SweTrack. Use at your own risk.
