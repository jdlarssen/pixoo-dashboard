"""Encapsulated dashboard loop state.

Centralizes bus/weather data, animation tracking, brightness, and
Discord bot death detection into a single object instead of loose
local variables.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from src.circuit_breaker import CircuitBreaker
from src.config import (
    BUS_REFRESH_INTERVAL,
    WEATHER_LAT,
    WEATHER_LON,
    WEATHER_REFRESH_INTERVAL,
    get_target_brightness,
)
from src.device.pixoo_client import PixooClient
from src.display.animation_selector import select_animation
from src.display.state import DisplayState
from src.display.weather_anim import WeatherAnimation
from src.providers.bus import fetch_bus_data
from src.providers.discord_bot import MessageBridge
from src.providers.discord_monitor import HealthTracker
from src.providers.weather import WeatherData, fetch_weather_safe
from src.staleness import StalenessTracker

logger = logging.getLogger(__name__)


class DashboardState:
    """Encapsulates the mutable state of the main dashboard loop.

    Centralizes bus/weather data, animation tracking, brightness, and
    Discord bot death detection into a single object instead of 8+
    loose local variables.
    """

    def __init__(self) -> None:
        self.last_state: DisplayState | None = None
        self.last_bus_fetch: float = 0.0
        self.last_weather_fetch: float = 0.0
        self.weather_anim: WeatherAnimation | None = None
        self.last_weather_group: str | None = None
        self.last_weather_night: bool | None = None
        self.last_precip_mm: float = 0.0
        self.last_wind_speed: float = 0.0
        self.last_brightness: int = -1
        self.needs_push: bool = False
        self.bot_dead_logged: bool = False

    def refresh_bus(
        self,
        now_mono: float,
        staleness: StalenessTracker,
        health_tracker: HealthTracker | None,
        bus_breaker: CircuitBreaker,
    ) -> None:
        """Fetch bus data and update staleness tracker."""
        if now_mono - self.last_bus_fetch < BUS_REFRESH_INTERVAL:
            return
        if not bus_breaker.should_attempt():
            self.last_bus_fetch = now_mono
            return
        fresh_bus = fetch_bus_data()
        self.last_bus_fetch = now_mono
        if fresh_bus != (None, None):
            staleness.update_bus(fresh_bus)
            bus_breaker.record_success()
            logger.info("Bus data refreshed: dir1=%s dir2=%s", fresh_bus[0], fresh_bus[1])
            if health_tracker:
                health_tracker.record_success("bus_api")
        else:
            bus_breaker.record_failure()
            logger.warning(
                "Bus fetch failed, using last-good data (age=%.0fs)",
                staleness.bus_data_age,
            )
            if health_tracker:
                health_tracker.record_failure("bus_api", "Bus API returned no data")

    def refresh_weather(
        self,
        now_mono: float,
        now_utc: datetime,
        staleness: StalenessTracker,
        health_tracker: HealthTracker | None,
        weather_breaker: CircuitBreaker,
        *,
        test_weather_data: WeatherData | None = None,
    ) -> None:
        """Fetch weather data and swap animation if needed."""
        if test_weather_data is not None:
            # TEST MODE: use hardcoded weather, skip API
            if staleness.last_good_weather is None:
                staleness.update_weather(test_weather_data)
                self._maybe_swap_animation(test_weather_data, now_utc)
                logger.info(
                    "TEST: weather animation: %s (night=%s, precip=%.1fmm, wind=%.1fm/s)",
                    self.last_weather_group,
                    self.last_weather_night,
                    self.last_precip_mm,
                    self.last_wind_speed,
                )
            return

        if now_mono - self.last_weather_fetch < WEATHER_REFRESH_INTERVAL:
            return
        if not weather_breaker.should_attempt():
            self.last_weather_fetch = now_mono
            return
        fresh_weather = fetch_weather_safe(WEATHER_LAT, WEATHER_LON)
        self.last_weather_fetch = now_mono
        if fresh_weather:
            staleness.update_weather(fresh_weather)
            weather_breaker.record_success()
            if health_tracker:
                health_tracker.record_success("weather_api")
            logger.info(
                "Weather refreshed: %.1f\u00b0C %s precip=%.1fmm",
                fresh_weather.temperature,
                fresh_weather.symbol_code,
                fresh_weather.precipitation_mm,
            )
            self._maybe_swap_animation(fresh_weather, now_utc)
        else:
            weather_breaker.record_failure()
            logger.warning(
                "Weather fetch failed, using last-good data (age=%.0fs)",
                staleness.weather_data_age,
            )
            if health_tracker:
                health_tracker.record_failure("weather_api", "Weather API returned no data")

    def _maybe_swap_animation(self, weather_data: WeatherData, now_utc: datetime) -> None:
        """Swap animation if weather conditions changed."""
        result = select_animation(
            weather_data,
            now_utc,
            self.last_weather_group,
            self.last_weather_night,
            self.last_precip_mm,
            self.last_wind_speed,
            lat=WEATHER_LAT,
            lon=WEATHER_LON,
        )
        (
            new_anim,
            self.last_weather_group,
            self.last_weather_night,
            self.last_precip_mm,
            self.last_wind_speed,
        ) = result
        if new_anim is not None:
            self.weather_anim = new_anim
            logger.info(
                "Weather animation: %s (night=%s, precip=%.1fmm, wind=%.1fm/s)",
                self.last_weather_group,
                self.last_weather_night,
                self.last_precip_mm,
                self.last_wind_speed,
            )

    def update_brightness(self, client: PixooClient, now_utc: datetime) -> None:
        """Adjust brightness based on astronomical darkness (only when target changes)."""
        target_brightness = get_target_brightness(now_utc, WEATHER_LAT, WEATHER_LON)
        if target_brightness != self.last_brightness:
            client.set_brightness(target_brightness)
            self.last_brightness = target_brightness
            logger.info("Brightness set to %d%%", target_brightness)

    def detect_bot_death(
        self,
        bot_dead_event: threading.Event | None,
        message_bridge: MessageBridge | None,
    ) -> None:
        """Detect Discord bot thread death -- log once, clear stale message."""
        if bot_dead_event is not None and bot_dead_event.is_set() and not self.bot_dead_logged:
            logger.warning("Discord bot thread has died -- clearing stale message")
            if message_bridge is not None:
                message_bridge.set_message(None)
            self.bot_dead_logged = True
