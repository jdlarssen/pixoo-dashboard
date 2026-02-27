"""Display state model for the Divoom Hub dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.providers.clock import format_date_norwegian, format_time

if TYPE_CHECKING:
    from src.providers.weather import WeatherData


@dataclass
class DisplayState:
    """Holds the current data to render on the display.

    Supports equality comparison via dataclass default __eq__,
    enabling the dirty flag pattern -- only re-render when state changes.
    """

    time_str: str  # e.g., "14:32"
    date_str: str  # e.g., "tor 20. feb"
    bus_direction1: tuple[int, ...] | None = None  # e.g., (5, 12) or None
    bus_direction2: tuple[int, ...] | None = None  # e.g., (3, 8) or None
    # Weather fields (all hashable types for dirty flag equality)
    weather_temp: int | None = None          # current temp, rounded to int
    weather_symbol: str | None = None        # MET symbol_code string
    weather_high: int | None = None          # today's high, rounded to int
    weather_low: int | None = None           # today's low, rounded to int
    weather_precip_mm: float | None = None   # next 1h precipitation in mm
    weather_is_day: bool = True              # day/night from symbol_code
    # Message override from Discord bot
    message_text: str | None = None          # persistent message text, or None
    # Birthday easter egg
    is_birthday: bool = False                # True on March 17 or December 16
    # Staleness flags for graceful error states
    bus_stale: bool = False                  # bus data is aging (>180s) but still usable
    bus_too_old: bool = False                # bus data too old (>600s) -- show dashes
    weather_stale: bool = False              # weather data is aging (>1800s) but still usable
    weather_too_old: bool = False            # weather data too old (>3600s) -- show dashes

    @classmethod
    def from_now(
        cls,
        dt: datetime,
        bus_data: tuple[list[int] | None, list[int] | None] = (None, None),
        weather_data: WeatherData | None = None,
        *,
        is_birthday: bool = False,
        message_text: str | None = None,
        bus_stale: bool = False,
        bus_too_old: bool = False,
        weather_stale: bool = False,
        weather_too_old: bool = False,
    ) -> DisplayState:
        """Create a DisplayState from a datetime and optional data sources.

        Args:
            dt: Datetime to derive state from.
            bus_data: Tuple of (direction1_minutes, direction2_minutes).
                Each element is a list of countdown minutes or None.
            weather_data: WeatherData from MET API or None.
            message_text: Persistent message from Discord bot, or None.
            bus_stale: True when bus data is stale but still usable.
            bus_too_old: True when bus data is too old to display.
            weather_stale: True when weather data is stale but still usable.
            weather_too_old: True when weather data is too old to display.

        Returns:
            DisplayState with formatted time, date, bus, weather, and staleness data.
        """
        weather_kwargs: dict = {}
        if weather_data is not None:
            weather_kwargs = {
                "weather_temp": round(weather_data.temperature),
                "weather_symbol": weather_data.symbol_code,
                "weather_high": round(weather_data.high_temp),
                "weather_low": round(weather_data.low_temp),
                "weather_precip_mm": weather_data.precipitation_mm,
                "weather_is_day": weather_data.is_day,
            }

        return cls(
            time_str=format_time(dt),
            date_str=format_date_norwegian(dt),
            bus_direction1=tuple(bus_data[0]) if bus_data[0] is not None else None,
            bus_direction2=tuple(bus_data[1]) if bus_data[1] is not None else None,
            message_text=message_text,
            is_birthday=is_birthday,
            bus_stale=bus_stale,
            bus_too_old=bus_too_old,
            weather_stale=weather_stale,
            weather_too_old=weather_too_old,
            **weather_kwargs,
        )
