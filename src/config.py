"""Configuration constants for Pixoo Dashboard."""

import ipaddress
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Lazy-loaded configuration singleton.

    All config values are loaded on first access via ``Config.get()``.
    This avoids module-level side effects (file I/O, env mutation) at
    import time.
    """

    _instance: "Config | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")

        # Project root (parent of src/)
        self.PROJECT_ROOT = Path(__file__).resolve().parent.parent

        # Device settings
        self.DEVICE_IP = os.environ.get("DIVOOM_IP", "192.168.1.100")
        self.DISPLAY_SIZE = 64
        # Font settings
        self.FONT_DIR = self.PROJECT_ROOT / "assets" / "fonts"
        self.FONT_SMALL = "5x8"  # for date and labels
        self.FONT_TINY = "4x6"  # for zone labels

        # Device safety
        self.MAX_BRIGHTNESS = 90  # cap at 90% -- full brightness can crash device

        # Brightness schedule (astronomical auto-dimming)
        self.BRIGHTNESS_NIGHT = 20
        self.BRIGHTNESS_DAY = self.MAX_BRIGHTNESS

        # --- Staleness thresholds (seconds) ---
        self.BUS_STALE_THRESHOLD = 180
        self.BUS_TOO_OLD_THRESHOLD = 600
        self.WEATHER_STALE_THRESHOLD = 1800
        self.WEATHER_TOO_OLD_THRESHOLD = 3600

        # --- Device recovery ---
        self.DEVICE_PING_INTERVAL = 30
        self.DEVICE_REBOOT_THRESHOLD = 5
        self.DEVICE_REBOOT_RECOVERY_WAIT = 30
        self.WATCHDOG_TIMEOUT = 120

        # --- Device communication ---
        self.DEVICE_HTTP_TIMEOUT = 5
        self.DEVICE_MIN_PUSH_INTERVAL = 1.0
        self.DEVICE_ERROR_COOLDOWN_BASE = 3.0
        self.DEVICE_ERROR_COOLDOWN_MAX = 60.0

        # --- Health tracker debounce (frozen to prevent accidental mutation) ---
        self.HEALTH_DEBOUNCE = MappingProxyType(
            {
                "bus_api": MappingProxyType({"failures_before_alert": 3, "repeat_interval": 900}),
                "weather_api": MappingProxyType(
                    {"failures_before_alert": 2, "repeat_interval": 1800}
                ),
                "device": MappingProxyType({"failures_before_alert": 5, "repeat_interval": 300}),
            }
        )
        self.HEALTH_DEBOUNCE_DEFAULT = MappingProxyType(
            {
                "failures_before_alert": 3,
                "repeat_interval": 600,
            }
        )

        # Bus departure settings (Entur JourneyPlanner v3 API)
        self.BUS_QUAY_DIRECTION1 = os.environ.get("BUS_QUAY_DIR1", "")
        self.BUS_QUAY_DIRECTION2 = os.environ.get("BUS_QUAY_DIR2", "")
        self.BUS_REFRESH_INTERVAL = 60
        self.BUS_NUM_DEPARTURES = 3
        self.ET_CLIENT_NAME = os.environ.get("ET_CLIENT_NAME", "pixoo-dashboard")
        self.ENTUR_API_URL = "https://api.entur.io/journey-planner/v3/graphql"

        # Weather settings (MET Norway Locationforecast 2.0 API)
        self.WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "0"))
        self.WEATHER_LON = float(os.environ.get("WEATHER_LON", "0"))
        self.WEATHER_REFRESH_INTERVAL = 600
        self.WEATHER_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        self.WEATHER_USER_AGENT = os.environ.get(
            "WEATHER_USER_AGENT",
            "pixoo-dashboard/1.0",
        )

        # Discord message override settings
        self.DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
        self.DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")
        self.DISCORD_MONITOR_CHANNEL_ID = os.environ.get(
            "DISCORD_MONITOR_CHANNEL_ID",
        )

        # Birthday easter egg
        self.BIRTHDAY_DATES_RAW = os.environ.get("BIRTHDAY_DATES", "")
        self.BIRTHDAY_DATES: list[tuple[int, int]] = []
        for _d in self.BIRTHDAY_DATES_RAW.split(","):
            _d = _d.strip()
            if _d:
                _parts = _d.split("-")
                if len(_parts) == 2:
                    try:
                        _month, _day = int(_parts[0]), int(_parts[1])
                        if 1 <= _month <= 12 and 1 <= _day <= 31:
                            self.BIRTHDAY_DATES.append((_month, _day))
                    except ValueError:
                        logger.warning(
                            "Ignoring invalid BIRTHDAY_DATES entry: %r",
                            _d,
                        )

    @classmethod
    def get(cls) -> "Config":
        """Return the singleton Config instance, creating it on first access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """For testing -- force reload on next access."""
        cls._instance = None


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

    cfg = Config.get()
    if is_dark(dt, lat, lon):
        return cfg.BRIGHTNESS_NIGHT
    return cfg.BRIGHTNESS_DAY


def validate_config() -> None:
    """Check that required config values are set. Exits with error if not."""
    cfg = Config.get()
    missing: list[str] = []

    if not os.environ.get("DIVOOM_IP"):
        missing.append("DIVOOM_IP")
    if not cfg.BUS_QUAY_DIRECTION1:
        missing.append("BUS_QUAY_DIR1")
    if not cfg.BUS_QUAY_DIRECTION2:
        missing.append("BUS_QUAY_DIR2")
    if not os.environ.get("WEATHER_LAT") or not os.environ.get("WEATHER_LON"):
        missing.append("WEATHER_LAT / WEATHER_LON")
    if not missing:
        if not (-90 <= cfg.WEATHER_LAT <= 90) or not (-180 <= cfg.WEATHER_LON <= 180):
            missing.append("WEATHER_LAT / WEATHER_LON (out of range)")
        elif (
            cfg.WEATHER_LAT == 0.0
            and cfg.WEATHER_LON == 0.0
            and (
                os.environ.get("WEATHER_LAT", "0") == "0"
                or os.environ.get("WEATHER_LON", "0") == "0"
            )
        ):
            missing.append("WEATHER_LAT / WEATHER_LON (defaulted to 0,0)")

    # Validate IP address format
    try:
        ip = ipaddress.ip_address(cfg.DEVICE_IP)
        if not ip.is_private:
            print(
                f"Warning: DIVOOM_IP ({cfg.DEVICE_IP}) is not a private IP address",
                file=sys.stderr,
            )
    except ValueError:
        missing.append(f"DIVOOM_IP (invalid IP address: {cfg.DEVICE_IP!r})")

    # Validate quay ID format
    for label, quay in [
        ("BUS_QUAY_DIR1", cfg.BUS_QUAY_DIRECTION1),
        ("BUS_QUAY_DIR2", cfg.BUS_QUAY_DIRECTION2),
    ]:
        if quay and not quay.startswith("NSR:Quay:"):
            print(
                f"Warning: {label} ({quay!r}) doesn't match expected format NSR:Quay:XXXXX",
                file=sys.stderr,
            )

    # Warn on partial Discord config
    discord_vars = {
        "DISCORD_BOT_TOKEN": cfg.DISCORD_BOT_TOKEN,
        "DISCORD_CHANNEL_ID": cfg.DISCORD_CHANNEL_ID,
    }
    set_vars = {k for k, v in discord_vars.items() if v}
    if set_vars and set_vars != set(discord_vars.keys()):
        missing_discord = set(discord_vars.keys()) - set_vars
        print(
            f"Warning: Discord partially configured. Set {missing_discord} to enable bot.",
            file=sys.stderr,
        )

    # Validate channel IDs are numeric
    if cfg.DISCORD_CHANNEL_ID:
        try:
            int(cfg.DISCORD_CHANNEL_ID)
        except ValueError:
            missing.append(f"DISCORD_CHANNEL_ID (not a valid integer: {cfg.DISCORD_CHANNEL_ID!r})")

    if missing:
        print(
            f"Missing required config (set in .env): {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            "Copy .env.example to .env and fill in your values.",
            file=sys.stderr,
        )
        sys.exit(1)


def __getattr__(name: str):
    """Module-level attribute access that delegates to Config singleton.

    This provides backward compatibility so that existing code like
    ``from src.config import DEVICE_IP`` continues to work without changes.
    """
    cfg = Config.get()
    try:
        return getattr(cfg, name)
    except AttributeError:
        raise AttributeError(f"module 'src.config' has no attribute {name!r}") from None
