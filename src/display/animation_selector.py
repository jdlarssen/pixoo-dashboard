"""Weather animation selection logic.

Determines when the weather animation needs swapping based on changes
in weather group, day/night status, precipitation category, or wind category.
"""

from __future__ import annotations

from datetime import datetime

from src.display.weather_anim import WeatherAnimation, get_animation
from src.display.weather_icons import symbol_to_group
from src.providers.sun import is_dark
from src.providers.weather import WeatherData


def precip_category(mm: float) -> str:
    """Classify precipitation into light/moderate/heavy for animation switching."""
    if mm < 1.0:
        return "light"
    elif mm <= 3.0:
        return "moderate"
    return "heavy"


def wind_category(speed: float) -> str:
    """Classify wind speed for animation switching."""
    if speed < 3.0:
        return "calm"
    elif speed <= 5.0:
        return "moderate"
    return "strong"


def should_swap_animation(
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
    if precip_category(precip_mm) != precip_category(last_precip_mm):
        return True
    if wind_category(wind_speed) != wind_category(last_wind_speed):
        return True
    return False


def select_animation(
    weather_data: WeatherData,
    now_utc: datetime,
    last_weather_group: str | None,
    last_weather_night: bool | None,
    last_precip_mm: float,
    last_wind_speed: float,
    *,
    lat: float,
    lon: float,
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
        lat: Latitude for day/night calculation.
        lon: Longitude for day/night calculation.

    Returns:
        Tuple of (new_animation_or_None, group, is_night, precip_mm, wind_speed).
        new_animation_or_None is a WeatherAnimation if conditions changed, else None.
    """
    new_group = symbol_to_group(weather_data.symbol_code)
    night = is_dark(now_utc, lat, lon)
    precip = weather_data.precipitation_mm
    wind = weather_data.wind_speed

    if should_swap_animation(
        new_group,
        night,
        precip,
        wind,
        last_weather_group,
        last_weather_night,
        last_precip_mm,
        last_wind_speed,
    ):
        anim = get_animation(
            new_group,
            is_night=night,
            precipitation_mm=precip,
            wind_speed=wind,
            wind_direction=weather_data.wind_from_direction,
        )
        return anim, new_group, night, precip, wind

    return None, new_group, night, precip, wind
