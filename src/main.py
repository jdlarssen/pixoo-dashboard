"""Divoom Hub dashboard entry point.

Renders a clock dashboard on the Pixoo 64 with Norwegian date formatting.
Updates the display only when the minute changes (dirty flag pattern).

Usage:
    python src/main.py --ip 192.168.1.100
    python src/main.py --simulated --save-frame
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work when run directly
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import (
    BUS_REFRESH_INTERVAL,
    DEVICE_IP,
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    FONT_DIR,
    FONT_SMALL,
    FONT_TINY,
    WEATHER_LAT,
    WEATHER_LON,
    WEATHER_REFRESH_INTERVAL,
    get_target_brightness,
    validate_config,
)
from src.display.renderer import render_frame
from src.display.state import DisplayState
from src.display.weather_anim import WeatherAnimation, get_animation
from src.display.weather_icons import symbol_to_group
from src.providers.bus import fetch_bus_data
from src.providers.discord_bot import MessageBridge, start_discord_bot
from src.providers.weather import WeatherData, fetch_weather_safe
from src.device.pixoo_client import PixooClient
from src.display.fonts import load_fonts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_font_map(font_dir: str) -> dict:
    """Load fonts and map them to logical names used by the renderer.

    Args:
        font_dir: Directory containing BDF font files.

    Returns:
        Dictionary with keys "small", "tiny" mapping to PIL fonts.
    """
    raw_fonts = load_fonts(font_dir)
    return {
        "small": raw_fonts[FONT_SMALL],
        "tiny": raw_fonts[FONT_TINY],
    }


def main_loop(
    client: PixooClient,
    fonts: dict,
    *,
    save_frame: bool = False,
    message_bridge: MessageBridge | None = None,
) -> None:
    """Run the dashboard main loop.

    Checks time every iteration. Pushes a frame when the display state
    changes or when the weather animation ticks a new frame.

    When weather animation is active, the loop runs at ~3 FPS (0.35s sleep)
    to produce smooth animation while staying above the device's 0.3s rate
    limit (prevents frame drops from timing jitter). Otherwise it sleeps 1 second.

    Args:
        client: Pixoo device client for pushing frames.
        fonts: Font dictionary with keys "small", "tiny".
        save_frame: If True, save each rendered frame to debug_frame.png.
        message_bridge: Optional MessageBridge from Discord bot for message override.
    """
    # --- TEST MODE: hardcode weather for visual testing ---
    # Set TEST_WEATHER env var to: clear, rain, snow, fog (cycles on restart)
    test_weather_mode = os.environ.get("TEST_WEATHER")
    test_weather_map = {
        "clear": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "rain": WeatherData(temperature=30, symbol_code="rain_day", high_temp=32, low_temp=22, precipitation_mm=5.0, is_day=True),
        "snow": WeatherData(temperature=30, symbol_code="snow_day", high_temp=32, low_temp=22, precipitation_mm=2.0, is_day=True),
        "fog": WeatherData(temperature=30, symbol_code="fog", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "cloudy": WeatherData(temperature=30, symbol_code="cloudy", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "sun": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "thunder": WeatherData(temperature=30, symbol_code="rainandthunder_day", high_temp=32, low_temp=22, precipitation_mm=8.0, is_day=True),
    }
    if test_weather_mode:
        logger.info("TEST MODE: weather=%s, temp=30°C, daytime", test_weather_mode)
    # --- END TEST MODE ---

    last_state = None
    last_bus_fetch = 0.0  # monotonic() is always > 60 on a running system
    last_weather_fetch = 0.0
    bus_data: tuple[list[int] | None, list[int] | None] = (None, None)
    weather_data: WeatherData | None = None
    weather_anim: WeatherAnimation | None = None
    last_weather_group: str | None = None
    needs_push = False

    # Staleness tracking -- preserve last-good data through API failures
    last_good_bus: tuple[list[int] | None, list[int] | None] = (None, None)
    last_good_bus_time: float = 0.0  # monotonic time of last successful bus fetch
    last_good_weather: WeatherData | None = None
    last_good_weather_time: float = 0.0  # monotonic time of last successful weather fetch

    # Brightness tracking -- only send brightness when target changes
    last_brightness: int = -1

    # Staleness thresholds (seconds)
    BUS_STALE_THRESHOLD = 180     # 3 minutes -- bus data is aging
    BUS_TOO_OLD_THRESHOLD = 600   # 10 minutes -- bus data is too old, show dashes
    WEATHER_STALE_THRESHOLD = 1800   # 30 minutes -- weather data is aging
    WEATHER_TOO_OLD_THRESHOLD = 3600  # 1 hour -- weather data is too old, show dashes

    while True:
        now_mono = time.monotonic()

        # Independent 60-second bus data refresh
        if now_mono - last_bus_fetch >= BUS_REFRESH_INTERVAL:
            fresh_bus = fetch_bus_data()
            last_bus_fetch = now_mono
            # Preserve last-good data on failure
            if fresh_bus != (None, None):
                bus_data = fresh_bus
                last_good_bus = fresh_bus
                last_good_bus_time = now_mono
                logger.info("Bus data refreshed: dir1=%s dir2=%s", bus_data[0], bus_data[1])
            else:
                # API failed -- keep using last-good data
                bus_data = last_good_bus
                logger.warning("Bus fetch failed, using last-good data (age=%.0fs)", now_mono - last_good_bus_time if last_good_bus_time > 0 else 0)

        # Independent 600-second weather data refresh
        if test_weather_mode and test_weather_mode in test_weather_map:
            # TEST MODE: use hardcoded weather, skip API
            if weather_data is None:
                weather_data = test_weather_map[test_weather_mode]
                last_good_weather = weather_data
                last_good_weather_time = now_mono
                new_group = symbol_to_group(weather_data.symbol_code)
                if new_group != last_weather_group:
                    weather_anim = get_animation(new_group)
                    last_weather_group = new_group
                    logger.info("TEST: weather animation: %s", new_group)
        elif now_mono - last_weather_fetch >= WEATHER_REFRESH_INTERVAL:
            fresh_weather = fetch_weather_safe(WEATHER_LAT, WEATHER_LON)
            last_weather_fetch = now_mono
            if fresh_weather:
                weather_data = fresh_weather
                last_good_weather = fresh_weather
                last_good_weather_time = now_mono
                logger.info(
                    "Weather refreshed: %.1f°C %s precip=%.1fmm",
                    weather_data.temperature,
                    weather_data.symbol_code,
                    weather_data.precipitation_mm,
                )
                # Swap animation if weather group changed
                new_group = symbol_to_group(weather_data.symbol_code)
                if new_group != last_weather_group:
                    weather_anim = get_animation(new_group)
                    last_weather_group = new_group
                    logger.info("Weather animation: %s", new_group)
            else:
                # API failed -- keep using last-good data
                weather_data = last_good_weather
                logger.warning("Weather fetch failed, using last-good data (age=%.0fs)", now_mono - last_good_weather_time if last_good_weather_time > 0 else 0)

        # Calculate staleness flags
        bus_age = now_mono - last_good_bus_time if last_good_bus_time > 0 else 0
        weather_age = now_mono - last_good_weather_time if last_good_weather_time > 0 else 0

        bus_stale = bus_age > BUS_STALE_THRESHOLD and last_good_bus_time > 0
        bus_too_old = bus_age > BUS_TOO_OLD_THRESHOLD and last_good_bus_time > 0
        weather_stale = weather_age > WEATHER_STALE_THRESHOLD and last_good_weather_time > 0
        weather_too_old = weather_age > WEATHER_TOO_OLD_THRESHOLD and last_good_weather_time > 0

        # When data is too old, pass None to show dash placeholders
        effective_bus = (None, None) if bus_too_old else bus_data
        effective_weather = None if weather_too_old else weather_data

        now = datetime.now()

        # Auto-brightness: adjust based on time of day (only when target changes)
        target_brightness = get_target_brightness(now.hour)
        if target_brightness != last_brightness:
            client.set_brightness(target_brightness)
            last_brightness = target_brightness
            logger.info("Brightness set to %d%%", target_brightness)

        # Read current message from Discord bot (thread-safe)
        current_message = message_bridge.current_message if message_bridge else None

        current_state = DisplayState.from_now(
            now,
            bus_data=effective_bus,
            weather_data=effective_weather,
            message_text=current_message,
            bus_stale=bus_stale,
            bus_too_old=bus_too_old,
            weather_stale=weather_stale,
            weather_too_old=weather_too_old,
        )

        # Check if state changed (minute change, bus update, weather update)
        state_changed = current_state != last_state
        if state_changed:
            needs_push = True
            last_state = current_state

        # Tick animation -- always produces a new frame when active
        anim_frame = None
        if weather_anim is not None:
            anim_frame = weather_anim.tick()
            needs_push = True  # animation always triggers a re-render

        if needs_push:
            frame = render_frame(current_state, fonts, anim_frame=anim_frame)

            if save_frame:
                frame.save("debug_frame.png")
                logger.info("Saved debug_frame.png")

            client.push_frame(frame)
            if state_changed:
                logger.info("Pushed frame: %s %s", current_state.time_str, current_state.date_str)
            needs_push = False

        # Sleep: 0.35s when animation is active (~3 FPS), 1s otherwise
        sleep_time = 0.35 if weather_anim is not None else 1.0
        time.sleep(sleep_time)


def main() -> None:
    """Parse arguments and start the dashboard."""
    validate_config()
    parser = argparse.ArgumentParser(description="Pixoo Dashboard - Pixoo 64 Dashboard")
    parser.add_argument(
        "--ip",
        default=DEVICE_IP,
        help=f"Pixoo 64 device IP address (default: {DEVICE_IP})",
    )
    parser.add_argument(
        "--simulated",
        action="store_true",
        default=False,
        help="Run in simulator mode (Tkinter window, no hardware needed)",
    )
    parser.add_argument(
        "--save-frame",
        action="store_true",
        default=False,
        help="Save each rendered frame to debug_frame.png",
    )
    args = parser.parse_args()

    logger.info("Loading fonts from %s", FONT_DIR)
    fonts = build_font_map(FONT_DIR)
    logger.info("Fonts loaded: %s", list(fonts.keys()))

    logger.info("Connecting to Pixoo 64 at %s (simulated=%s)", args.ip, args.simulated)
    client = PixooClient(ip=args.ip, simulated=args.simulated)

    # Start Discord bot in background thread (optional)
    message_bridge = start_discord_bot(DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID)
    if message_bridge:
        logger.info("Discord bot started for message override")
    else:
        logger.info("Discord bot not configured (no DISCORD_BOT_TOKEN/DISCORD_CHANNEL_ID)")

    logger.info("Starting dashboard main loop (Ctrl+C to stop)")
    try:
        main_loop(client, fonts, save_frame=args.save_frame, message_bridge=message_bridge)
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
