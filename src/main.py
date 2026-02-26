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
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work when run directly
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import (
    BUS_QUAY_DIRECTION1,
    BUS_QUAY_DIRECTION2,
    BUS_REFRESH_INTERVAL,
    DEVICE_IP,
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_MONITOR_CHANNEL_ID,
    FONT_DIR,
    FONT_SMALL,
    FONT_TINY,
    WATCHDOG_TIMEOUT,
    WEATHER_LAT,
    WEATHER_LON,
    WEATHER_REFRESH_INTERVAL,
    get_target_brightness,
    validate_config,
)
from src.device.keepalive import DeviceKeepAlive
from src.device.pixoo_client import PixooClient
from src.display.fonts import load_fonts
from src.display.renderer import render_frame
from src.display.state import DisplayState
from src.display.weather_anim import WeatherAnimation, get_animation
from src.display.weather_icons import symbol_to_group
from src.providers.bus import fetch_bus_data, fetch_quay_name
from src.providers.discord_bot import MessageBridge, start_discord_bot
from src.providers.discord_monitor import HealthTracker, MonitorBridge, startup_embed, shutdown_embed
from src.providers.sun import is_dark
from src.providers.weather import WeatherData, fetch_weather_safe
from src.staleness import StalenessTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _watchdog_thread(heartbeat_ref: list[float], timeout: float = WATCHDOG_TIMEOUT) -> None:
    """Monitor main loop heartbeat; force-kill if stale.

    Runs as a daemon thread. Checks every 30s whether the main loop
    has updated its heartbeat timestamp. If the heartbeat is older than
    *timeout* seconds, logs a critical message and calls os._exit(1)
    so launchd can restart the process.
    """
    while True:
        time.sleep(30)
        elapsed = time.monotonic() - heartbeat_ref[0]
        if elapsed > timeout:
            logger.critical(
                "Watchdog: main loop hung for %.0fs (threshold %ds), forcing exit",
                elapsed,
                timeout,
            )
            os._exit(1)


def _reverse_geocode(lat: float, lon: float) -> str | None:
    """Resolve lat/lon to a city name via OpenStreetMap Nominatim."""
    import requests as _requests
    try:
        resp = _requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
            headers={"User-Agent": "divoom-hub/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        return (
            address.get("city") or address.get("town")
            or address.get("municipality") or address.get("village")
        )
    except (_requests.RequestException, KeyError, ValueError):
        logger.debug("Reverse geocode failed for %s, %s", lat, lon)
        return None


def _precip_category(mm: float) -> str:
    """Classify precipitation into light/moderate/heavy for animation switching."""
    if mm < 1.0:
        return "light"
    elif mm <= 3.0:
        return "moderate"
    return "heavy"


def _wind_category(speed: float) -> str:
    """Classify wind speed for animation switching."""
    if speed < 3.0:
        return "calm"
    elif speed <= 5.0:
        return "moderate"
    return "strong"


def _should_swap_animation(
    new_group: str,
    is_night: bool,
    precip_mm: float,
    wind_speed: float,
    last_group: str | None,
    last_night: bool | None,
    last_precip_mm: float,
    last_wind_speed: float,
) -> bool:
    """Check if weather animation needs to be swapped.

    Returns True when any of the four tracked dimensions (weather group,
    day/night, precipitation category, wind category) has changed.
    """
    if new_group != last_group:
        return True
    if is_night != last_night:
        return True
    if _precip_category(precip_mm) != _precip_category(last_precip_mm):
        return True
    if _wind_category(wind_speed) != _wind_category(last_wind_speed):
        return True
    return False


def _select_animation(
    weather_data: WeatherData,
    now_utc: datetime,
    last_weather_group: str | None,
    last_weather_night: bool | None,
    last_precip_mm: float,
    last_wind_speed: float,
) -> tuple[WeatherAnimation | None, str, bool, float, float]:
    """Decide whether to swap the weather animation and return the new one.

    Compares the current weather conditions against the last-known state.
    If the weather group, day/night status, precipitation category, or
    wind category has changed, creates and returns a new animation.

    Args:
        weather_data: Current weather data.
        now_utc: Current UTC time (for day/night check).
        last_weather_group: Previous weather group (or None on first call).
        last_weather_night: Previous night flag (or None on first call).
        last_precip_mm: Previous precipitation in mm.
        last_wind_speed: Previous wind speed in m/s.

    Returns:
        Tuple of (new_animation_or_None, group, is_night, precip_mm, wind_speed).
        new_animation_or_None is a WeatherAnimation if conditions changed, else None.
    """
    new_group = symbol_to_group(weather_data.symbol_code)
    is_night = is_dark(now_utc, WEATHER_LAT, WEATHER_LON)
    precip = weather_data.precipitation_mm
    wind = weather_data.wind_speed

    if _should_swap_animation(
        new_group, is_night, precip, wind,
        last_weather_group, last_weather_night, last_precip_mm, last_wind_speed,
    ):
        anim = get_animation(
            new_group,
            is_night=is_night,
            precipitation_mm=precip,
            wind_speed=wind,
            wind_direction=weather_data.wind_from_direction,
        )
        return anim, new_group, is_night, precip, wind

    return None, new_group, is_night, precip, wind


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
    health_tracker: HealthTracker | None = None,
    bot_dead_event: threading.Event | None = None,
) -> None:
    """Run the dashboard main loop.

    Checks time every iteration. Pushes a frame when the display state
    changes or when the weather animation ticks a new frame.

    When weather animation is active, the loop runs at ~1 FPS (1.0s sleep).
    The Pixoo 64 device can only reliably handle ~1 HTTP push per second;
    faster rates overwhelm its embedded HTTP server, causing connection
    resets and eventual device freezes. Without animation, also sleeps 1s.

    Args:
        client: Pixoo device client for pushing frames.
        fonts: Font dictionary with keys "small", "tiny".
        save_frame: If True, save each rendered frame to debug_frame.png.
        message_bridge: Optional MessageBridge from Discord bot for message override.
        health_tracker: Optional HealthTracker for monitoring integration.
        bot_dead_event: Optional threading.Event set when Discord bot thread dies.
    """
    # --- TEST MODE: hardcode weather for visual testing ---
    # Set TEST_WEATHER env var to: clear, rain, snow, fog (cycles on restart)
    test_weather_mode = os.environ.get("TEST_WEATHER")
    test_weather_map = {
        "clear": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True, wind_speed=2.0, wind_from_direction=180.0),
        "rain": WeatherData(temperature=30, symbol_code="rain_day", high_temp=32, low_temp=22, precipitation_mm=5.0, is_day=True, wind_speed=8.0, wind_from_direction=270.0),
        "snow": WeatherData(temperature=30, symbol_code="snow_day", high_temp=32, low_temp=22, precipitation_mm=2.0, is_day=True, wind_speed=5.0, wind_from_direction=200.0),
        "fog": WeatherData(temperature=30, symbol_code="fog", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "cloudy": WeatherData(temperature=30, symbol_code="cloudy", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "sun": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
        "thunder": WeatherData(temperature=30, symbol_code="rainandthunder_day", high_temp=32, low_temp=22, precipitation_mm=8.0, is_day=True, wind_speed=12.0, wind_from_direction=250.0),
    }
    if test_weather_mode:
        logger.info("TEST MODE: weather=%s, temp=30\u00b0C, daytime", test_weather_mode)
    # --- END TEST MODE ---

    last_state = None
    last_bus_fetch = 0.0  # monotonic() is always > 60 on a running system
    last_weather_fetch = 0.0
    bus_data: tuple[list[int] | None, list[int] | None] = (None, None)
    weather_data: WeatherData | None = None
    weather_anim: WeatherAnimation | None = None
    last_weather_group: str | None = None
    last_weather_night: bool | None = None
    last_precip_mm: float = 0.0
    last_wind_speed: float = 0.0
    needs_push = False

    # Watchdog: detect hung main loop and force-exit for launchd restart
    heartbeat = [time.monotonic()]
    watchdog = threading.Thread(target=_watchdog_thread, args=(heartbeat,), daemon=True)
    watchdog.start()
    logger.info("Watchdog started (timeout=%ds)", WATCHDOG_TIMEOUT)

    # Delegate device keep-alive and staleness tracking to dedicated classes
    keepalive = DeviceKeepAlive()
    staleness = StalenessTracker()

    # Brightness tracking -- only send brightness when target changes
    last_brightness: int = -1

    # Discord bot death detection -- log once, clear stale message
    bot_dead_logged = False

    while True:
        now_mono = time.monotonic()
        now_utc = datetime.now(timezone.utc)

        # Detect Discord bot thread death -- log once, clear stale message
        if bot_dead_event is not None and bot_dead_event.is_set() and not bot_dead_logged:
            logger.warning("Discord bot thread has died -- clearing stale message")
            if message_bridge is not None:
                message_bridge.set_message(None)
            bot_dead_logged = True

        # Independent 60-second bus data refresh
        if now_mono - last_bus_fetch >= BUS_REFRESH_INTERVAL:
            fresh_bus = fetch_bus_data()
            last_bus_fetch = now_mono
            # Preserve last-good data on failure
            if fresh_bus != (None, None):
                bus_data = fresh_bus
                staleness.update_bus(fresh_bus)
                logger.info("Bus data refreshed: dir1=%s dir2=%s", bus_data[0], bus_data[1])
                if health_tracker:
                    health_tracker.record_success("bus_api")
            else:
                # API failed -- keep using last-good data
                bus_data = staleness.last_good_bus
                logger.warning("Bus fetch failed, using last-good data (age=%.0fs)", staleness.bus_data_age)
                if health_tracker:
                    health_tracker.record_failure("bus_api", "Bus API returned no data")

        # Independent 600-second weather data refresh
        if test_weather_mode and test_weather_mode in test_weather_map:
            # TEST MODE: use hardcoded weather, skip API
            if weather_data is None:
                weather_data = test_weather_map[test_weather_mode]
                staleness.update_weather(weather_data)
                result = _select_animation(
                    weather_data, now_utc,
                    last_weather_group, last_weather_night,
                    last_precip_mm, last_wind_speed,
                )
                new_anim, last_weather_group, last_weather_night, last_precip_mm, last_wind_speed = result
                if new_anim is not None:
                    weather_anim = new_anim
                    logger.info(
                        "TEST: weather animation: %s (night=%s, precip=%.1fmm, wind=%.1fm/s)",
                        last_weather_group, last_weather_night, last_precip_mm, last_wind_speed,
                    )
        elif now_mono - last_weather_fetch >= WEATHER_REFRESH_INTERVAL:
            fresh_weather = fetch_weather_safe(WEATHER_LAT, WEATHER_LON)
            last_weather_fetch = now_mono
            if fresh_weather:
                weather_data = fresh_weather
                staleness.update_weather(fresh_weather)
                if health_tracker:
                    health_tracker.record_success("weather_api")
                logger.info(
                    "Weather refreshed: %.1f\u00b0C %s precip=%.1fmm",
                    weather_data.temperature,
                    weather_data.symbol_code,
                    weather_data.precipitation_mm,
                )
                # Swap animation if weather group, day/night, or rain intensity changed
                result = _select_animation(
                    weather_data, now_utc,
                    last_weather_group, last_weather_night,
                    last_precip_mm, last_wind_speed,
                )
                new_anim, last_weather_group, last_weather_night, last_precip_mm, last_wind_speed = result
                if new_anim is not None:
                    weather_anim = new_anim
                    logger.info(
                        "Weather animation: %s (night=%s, precip=%.1fmm, wind=%.1fm/s)",
                        last_weather_group, last_weather_night, last_precip_mm, last_wind_speed,
                    )
            else:
                # API failed -- keep using last-good data
                weather_data = staleness.last_good_weather
                logger.warning("Weather fetch failed, using last-good data (age=%.0fs)", staleness.weather_data_age)
                if health_tracker:
                    health_tracker.record_failure("weather_api", "Weather API returned no data")

        # Calculate staleness flags and effective data from the tracker
        effective_bus, bus_stale, bus_too_old = staleness.get_effective_bus()
        effective_weather, weather_stale, weather_too_old = staleness.get_effective_weather()

        # When bus/weather data is not too old, prefer the fresh fetch result
        # (which may differ from last_good if we just fetched and got a failure
        # -- in that case bus_data/weather_data already fell back to last_good).
        if not bus_too_old:
            effective_bus = bus_data
        if not weather_too_old:
            effective_weather = weather_data

        now = datetime.now()

        # Auto-brightness: adjust based on astronomical darkness (only when target changes)
        target_brightness = get_target_brightness(now_utc, WEATHER_LAT, WEATHER_LON)
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

            push_result = client.push_frame(frame)
            if push_result is True:
                keepalive.record_success()
                if health_tracker:
                    health_tracker.record_success("device")
                if state_changed:
                    logger.info("Pushed frame: %s %s", current_state.time_str, current_state.date_str)
            elif push_result is False:
                keepalive.record_failure()
                if health_tracker:
                    health_tracker.record_failure("device", "Device unreachable")
            # push_result is None means skipped (rate limit / cooldown) -- no health action
            needs_push = False

        # Device keep-alive ping + auto-reboot recovery
        keepalive.tick(client, now_mono, health_tracker=health_tracker)

        # Sleep 1s always.  The Pixoo 64 can handle ~1 push/second max.
        # Animation particles advance one step per tick, producing gentle
        # motion at 1 FPS that the LED display renders smoothly.
        time.sleep(1.0)

        # Update watchdog heartbeat after each successful iteration
        heartbeat[0] = time.monotonic()


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

    # Set up monitoring (optional -- requires DISCORD_MONITOR_CHANNEL_ID)
    monitor_bridge = None
    health_tracker = HealthTracker(monitor=None)

    def on_ready_callback(bot_client):
        nonlocal monitor_bridge
        if DISCORD_MONITOR_CHANNEL_ID:
            monitor_bridge = MonitorBridge(bot_client, int(DISCORD_MONITOR_CHANNEL_ID))
            health_tracker.set_monitor(monitor_bridge)
            try:
                bus_name1 = fetch_quay_name(BUS_QUAY_DIRECTION1)
                bus_name2 = fetch_quay_name(BUS_QUAY_DIRECTION2)
                weather_location = _reverse_geocode(WEATHER_LAT, WEATHER_LON)
                embed = startup_embed(
                    pixoo_ip=args.ip,
                    bus_quay_dir1=BUS_QUAY_DIRECTION1,
                    bus_quay_dir2=BUS_QUAY_DIRECTION2,
                    weather_lat=WEATHER_LAT,
                    weather_lon=WEATHER_LON,
                    bus_name_dir1=bus_name1,
                    bus_name_dir2=bus_name2,
                    weather_location=weather_location,
                )
                if monitor_bridge.send_embed(embed):
                    logger.info("Monitoring active -- startup embed sent to channel %s", DISCORD_MONITOR_CHANNEL_ID)
                else:
                    logger.warning("Monitoring active -- startup embed failed for channel %s", DISCORD_MONITOR_CHANNEL_ID)
            except Exception:
                logger.exception("Failed to send startup embed")

    # Start Discord bot in background thread (optional)
    bot_dead_event = None
    if DISCORD_MONITOR_CHANNEL_ID:
        result = start_discord_bot(
            DISCORD_BOT_TOKEN,
            DISCORD_CHANNEL_ID,
            monitor_channel_id=DISCORD_MONITOR_CHANNEL_ID,
            health_tracker=health_tracker,
            on_ready_callback=on_ready_callback,
        )
    else:
        result = start_discord_bot(DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID)
        logger.info("Discord monitoring not configured (no DISCORD_MONITOR_CHANNEL_ID)")

    if result:
        message_bridge, bot_dead_event = result
        logger.info("Discord bot started for message override")
    else:
        message_bridge = None
        logger.info("Discord bot not configured (no DISCORD_BOT_TOKEN/DISCORD_CHANNEL_ID)")

    logger.info("Starting dashboard main loop (Ctrl+C to stop)")
    try:
        main_loop(
            client,
            fonts,
            save_frame=args.save_frame,
            message_bridge=message_bridge,
            health_tracker=health_tracker,
            bot_dead_event=bot_dead_event,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down")
        # Best-effort shutdown embed (2-second timeout)
        if monitor_bridge:
            try:
                embed = shutdown_embed()
                monitor_bridge.send_embed(embed)
                logger.info("Shutdown embed sent")
            except Exception:
                logger.debug("Could not send shutdown embed (expected on forced kill)")


if __name__ == "__main__":
    main()
