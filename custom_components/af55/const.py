"""Constants for the WNC AF55 integration."""

DOMAIN = "af55"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_HOST = "host"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_HOST = "192.168.1.1"
DEFAULT_USERNAME = "admin"
DEFAULT_VERIFY_SSL = False
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600
