DOMAIN = "swetrack"

CONF_TOKEN = "token"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FETCH_EXTENDED = "fetch_extended"

DEFAULT_BASE_URL = "https://api.cloudappapi.com/publicapi/v1"
DEFAULT_SCAN_INTERVAL = 300  # seconds (5 min) - respects typical daily quotas better
DEFAULT_FETCH_EXTENDED = True  # you can turn this off in Options

PLATFORMS = ["device_tracker", "sensor", "binary_sensor"]
