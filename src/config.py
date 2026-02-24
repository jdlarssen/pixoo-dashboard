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
# Example: "03-17,12-16" for March 17 and December 16
BIRTHDAY_DATES_RAW = os.environ.get("BIRTHDAY_DATES", "")
BIRTHDAY_DATES: list[tuple[int, int]] = []
for _d in BIRTHDAY_DATES_RAW.split(","):
    _d = _d.strip()
    if _d:
        _parts = _d.split("-")
        if len(_parts) == 2:
            BIRTHDAY_DATES.append((int(_parts[0]), int(_parts[1])))


def validate_config() -> None:
    """Check that required config values are set. Exits with error if not."""
    missing = []
    if not BUS_QUAY_DIRECTION1:
        missing.append("BUS_QUAY_DIR1")
    if not BUS_QUAY_DIRECTION2:
        missing.append("BUS_QUAY_DIR2")
    if WEATHER_LAT == 0 and WEATHER_LON == 0:
        missing.append("WEATHER_LAT / WEATHER_LON")
    if missing:
        print(f"Missing required config (set in .env): {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your values.", file=sys.stderr)
        sys.exit(1)
