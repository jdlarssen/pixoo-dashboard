"""Configuration constants for Pixoo Dashboard."""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Device settings
DEVICE_IP = os.environ.get("DIVOOM_IP", "192.168.1.100")
DISPLAY_SIZE = 64
# Font settings
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_SMALL = "5x8"    # for date and labels
FONT_TINY = "4x6"     # for zone labels

# Device safety
MAX_BRIGHTNESS = 90  # cap at 90% -- full brightness can crash device

# Brightness schedule (astronomical auto-dimming)
BRIGHTNESS_NIGHT = 20     # 20% -- within user's 15-25% range, readable without lighting room
BRIGHTNESS_DAY = 100      # 100% -- PixooClient caps at MAX_BRIGHTNESS (90%)

# --- Staleness thresholds (seconds) ---
BUS_STALE_THRESHOLD = 180          # 3 minutes -- bus data is aging
BUS_TOO_OLD_THRESHOLD = 600        # 10 minutes -- bus data is too old, show dashes
WEATHER_STALE_THRESHOLD = 1800     # 30 minutes -- weather data is aging
WEATHER_TOO_OLD_THRESHOLD = 3600   # 1 hour -- weather data is too old, show dashes

# --- Device recovery ---
DEVICE_PING_INTERVAL = 30          # seconds between keep-alive pings
DEVICE_REBOOT_THRESHOLD = 5        # consecutive failures before reboot
DEVICE_REBOOT_RECOVERY_WAIT = 30   # seconds to wait after reboot for device to reconnect
WATCHDOG_TIMEOUT = 120             # seconds before watchdog force-kills a hung process

# --- Device communication ---
DEVICE_HTTP_TIMEOUT = 5            # seconds for HTTP requests to device
DEVICE_MIN_PUSH_INTERVAL = 1.0     # minimum seconds between frame pushes
DEVICE_ERROR_COOLDOWN_BASE = 3.0   # initial cooldown after first failure (seconds)
DEVICE_ERROR_COOLDOWN_MAX = 60.0   # maximum cooldown cap (seconds)

# --- Health tracker debounce ---
HEALTH_DEBOUNCE = {
    "bus_api": {"failures_before_alert": 3, "repeat_interval": 900},
    "weather_api": {"failures_before_alert": 2, "repeat_interval": 1800},
    "device": {"failures_before_alert": 5, "repeat_interval": 300},
}
HEALTH_DEBOUNCE_DEFAULT = {"failures_before_alert": 3, "repeat_interval": 600}


def get_target_brightness(dt: datetime, lat: float, lon: float) -> int:
    """Return target brightness based on astronomical darkness.

    Uses civil twilight (sun 6 deg below horizon) from the astral library
    instead of hardcoded hours.

    Args:
        dt: Current timezone-aware datetime.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Target brightness percentage (0-100).
    """
    from src.providers.sun import is_dark
    if is_dark(dt, lat, lon):
        return BRIGHTNESS_NIGHT
    return BRIGHTNESS_DAY

# Bus departure settings (Entur JourneyPlanner v3 API)
BUS_QUAY_DIRECTION1 = os.environ.get("BUS_QUAY_DIR1", "")
BUS_QUAY_DIRECTION2 = os.environ.get("BUS_QUAY_DIR2", "")
BUS_REFRESH_INTERVAL = 60  # seconds between bus API fetches
BUS_NUM_DEPARTURES = 3  # number of departures to show per direction
ET_CLIENT_NAME = os.environ.get("ET_CLIENT_NAME", "pixoo-dashboard")
ENTUR_API_URL = "https://api.entur.io/journey-planner/v3/graphql"

# Weather settings (MET Norway Locationforecast 2.0 API)
WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "0"))
WEATHER_LON = float(os.environ.get("WEATHER_LON", "0"))
WEATHER_REFRESH_INTERVAL = 600  # seconds between weather API fetches (10 min)
WEATHER_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
WEATHER_USER_AGENT = os.environ.get("WEATHER_USER_AGENT", "pixoo-dashboard/1.0")

# Discord message override settings (optional -- bot only starts if both are set)
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")  # None if not configured
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")  # None if not configured

# Discord monitoring channel for remote health alerts (optional)
# Sends error/recovery embeds -- silence means healthy
DISCORD_MONITOR_CHANNEL_ID = os.environ.get("DISCORD_MONITOR_CHANNEL_ID")  # None if not configured

# Birthday easter egg (optional -- comma-separated MM-DD dates)
# Example: "01-01,06-15" for March 17 and December 16
BIRTHDAY_DATES_RAW = os.environ.get("BIRTHDAY_DATES", "")
BIRTHDAY_DATES: list[tuple[int, int]] = []
for _d in BIRTHDAY_DATES_RAW.split(","):
    _d = _d.strip()
    if _d:
        _parts = _d.split("-")
        if len(_parts) == 2:
            try:
                _month, _day = int(_parts[0]), int(_parts[1])
                if 1 <= _month <= 12 and 1 <= _day <= 31:
                    BIRTHDAY_DATES.append((_month, _day))
            except ValueError:
                pass


def validate_config() -> None:
    """Check that required config values are set. Exits with error if not."""
    missing = []
    if not BUS_QUAY_DIRECTION1:
        missing.append("BUS_QUAY_DIR1")
    if not BUS_QUAY_DIRECTION2:
        missing.append("BUS_QUAY_DIR2")
    if not os.environ.get("WEATHER_LAT") or not os.environ.get("WEATHER_LON"):
        missing.append("WEATHER_LAT / WEATHER_LON")
    if missing:
        print(f"Missing required config (set in .env): {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your values.", file=sys.stderr)
        sys.exit(1)
