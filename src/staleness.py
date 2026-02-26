"""Staleness tracking for bus and weather data.

Preserves last-good data through API failures and tracks how old it is.
When data exceeds a threshold, it is marked stale (visual indicator);
when it exceeds a second, higher threshold, it is discarded (show dashes).
"""

from __future__ import annotations

import logging
import time

from src.config import (
    BUS_STALE_THRESHOLD,
    BUS_TOO_OLD_THRESHOLD,
    WEATHER_STALE_THRESHOLD,
    WEATHER_TOO_OLD_THRESHOLD,
)
from src.providers.weather import WeatherData

logger = logging.getLogger(__name__)

BusData = tuple[list[int] | None, list[int] | None]


class StalenessTracker:
    """Track freshness of bus and weather data across API fetch cycles.

    Stores last-good data and timestamps. Provides ``get_effective_*``
    methods that return the data to display along with staleness flags.
    """

    def __init__(self) -> None:
        self._last_good_bus: BusData = (None, None)
        self._last_good_bus_time: float = 0.0

        self._last_good_weather: WeatherData | None = None
        self._last_good_weather_time: float = 0.0

    # -- Bus ------------------------------------------------------------------

    def update_bus(self, data: BusData) -> None:
        """Record a successful bus fetch."""
        self._last_good_bus = data
        self._last_good_bus_time = time.monotonic()

    @property
    def last_good_bus(self) -> BusData:
        """Return the most recent successful bus data (may be stale)."""
        return self._last_good_bus

    @property
    def bus_data_age(self) -> float:
        """Return age in seconds of last good bus data, or 0 if never fetched."""
        if self._last_good_bus_time > 0:
            return time.monotonic() - self._last_good_bus_time
        return 0.0

    def get_effective_bus(self) -> tuple[BusData, bool, bool]:
        """Return ``(data, is_stale, is_too_old)`` for bus data.

        * *is_stale*: data exists but exceeds the stale threshold.
        * *is_too_old*: data exceeds the too-old threshold -- caller should
          show dash placeholders instead.
        """
        age = self.bus_data_age

        is_stale = age > BUS_STALE_THRESHOLD and self._last_good_bus_time > 0
        is_too_old = age > BUS_TOO_OLD_THRESHOLD and self._last_good_bus_time > 0

        effective = (None, None) if is_too_old else self._last_good_bus
        return effective, is_stale, is_too_old

    # -- Weather --------------------------------------------------------------

    def update_weather(self, data: WeatherData) -> None:
        """Record a successful weather fetch."""
        self._last_good_weather = data
        self._last_good_weather_time = time.monotonic()

    @property
    def last_good_weather(self) -> WeatherData | None:
        """Return the most recent successful weather data (may be stale)."""
        return self._last_good_weather

    @property
    def weather_data_age(self) -> float:
        """Return age in seconds of last good weather data, or 0 if never fetched."""
        if self._last_good_weather_time > 0:
            return time.monotonic() - self._last_good_weather_time
        return 0.0

    def get_effective_weather(self) -> tuple[WeatherData | None, bool, bool]:
        """Return ``(data, is_stale, is_too_old)`` for weather data.

        * *is_stale*: data exists but exceeds the stale threshold.
        * *is_too_old*: data exceeds the too-old threshold -- caller should
          show dash placeholders instead.
        """
        age = self.weather_data_age

        is_stale = age > WEATHER_STALE_THRESHOLD and self._last_good_weather_time > 0
        is_too_old = age > WEATHER_TOO_OLD_THRESHOLD and self._last_good_weather_time > 0

        effective = None if is_too_old else self._last_good_weather
        return effective, is_stale, is_too_old
