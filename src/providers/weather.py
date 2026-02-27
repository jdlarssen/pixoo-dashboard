"""Weather provider using the MET Norway Locationforecast 2.0 API.

Fetches current weather conditions, today's high/low temperatures, and
precipitation data for a given location. Uses If-Modified-Since caching
to respect MET API terms of service.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from src.config import WEATHER_API_URL, WEATHER_USER_AGENT

logger = logging.getLogger(__name__)

# Module-level cache for API responses (If-Modified-Since pattern)
_cached_data: dict | None = None
_last_modified: str | None = None
_cache_lock = threading.Lock()


@dataclass
class WeatherData:
    """Current weather conditions from MET Locationforecast 2.0."""

    temperature: float       # current temp in Celsius
    symbol_code: str         # MET symbol code, e.g. "partlycloudy_day"
    high_temp: float         # today's forecast high
    low_temp: float          # today's forecast low
    precipitation_mm: float  # next 1h precipitation amount in mm
    is_day: bool             # derived from symbol_code suffix
    wind_speed: float = 0.0           # wind speed in m/s
    wind_from_direction: float = 0.0  # meteorological wind direction in degrees


def _parse_is_day(symbol_code: str) -> bool:
    """Determine if it's daytime from the MET symbol_code suffix.

    MET appends _day, _night, or _polartwilight to symbol codes.
    Codes without a suffix (e.g. "cloudy", "fog") are day-neutral.

    Args:
        symbol_code: MET weather symbol code string.

    Returns:
        True if daytime or neutral, False if nighttime or polar twilight.
    """
    return "_night" not in symbol_code and "_polartwilight" not in symbol_code


def _parse_current(timeseries: list[dict]) -> dict:
    """Extract current conditions from the first timeseries entry.

    Args:
        timeseries: List of forecast timeseries entries from MET API.

    Returns:
        Dictionary with temperature, symbol_code, precipitation_mm, is_day.
    """
    if not timeseries:
        raise ValueError("Empty timeseries in weather response")
    entry = timeseries[0]
    instant = entry.get("data", {}).get("instant", {}).get("details", {})
    temp = instant.get("air_temperature")
    if temp is None:
        raise ValueError(
            "Missing 'air_temperature' in weather response instant details"
        )

    next_1h = entry.get("data", {}).get("next_1_hours", {})
    symbol_code = next_1h.get("summary", {}).get("symbol_code", "cloudy")

    return {
        "temperature": temp,
        "symbol_code": symbol_code,
        "precipitation_mm": next_1h.get("details", {}).get("precipitation_amount", 0.0),
        "is_day": _parse_is_day(symbol_code),
        "wind_speed": instant.get("wind_speed", 0.0),
        "wind_from_direction": instant.get("wind_from_direction", 0.0),
    }


def _parse_high_low(timeseries: list[dict]) -> tuple[float, float]:
    """Scan today's timeseries entries for temperature extremes.

    Collects all instant air_temperature values for today's date and
    returns the (max, min). Falls back to the first entry's next_6_hours
    forecast if no today entries are found.

    Args:
        timeseries: List of forecast timeseries entries from MET API.

    Returns:
        Tuple of (high_temp, low_temp) in Celsius.
    """
    today_str = datetime.now(timezone.utc).date().isoformat()
    temps = []
    for entry in timeseries:
        time_val = entry.get("time", "")
        if not time_val.startswith(today_str):
            continue
        temp = (
            entry.get("data", {})
            .get("instant", {})
            .get("details", {})
            .get("air_temperature")
        )
        if temp is None:
            logger.warning(
                "Skipping timeseries entry at %s: missing air_temperature",
                time_val,
            )
            continue
        temps.append(temp)

    if temps:
        return (max(temps), min(temps))

    # Fallback: use next_6_hours from first entry
    first = timeseries[0].get("data", {}) if timeseries else {}
    n6h = first.get("next_6_hours", {}).get("details", {})
    high = n6h.get("air_temperature_max")
    low = n6h.get("air_temperature_min")
    if high is not None and low is not None:
        return (high, low)

    # Last resort: use current temperature as both high and low
    current_temp = (
        first.get("instant", {}).get("details", {}).get("air_temperature")
    )
    if current_temp is not None:
        return (current_temp, current_temp)

    return (0.0, 0.0)


def fetch_weather(lat: float, lon: float) -> WeatherData:
    """Fetch current weather from MET Locationforecast 2.0.

    Uses If-Modified-Since caching to avoid redundant downloads.
    MET API updates roughly every 10 minutes.

    Args:
        lat: Latitude (decimal degrees).
        lon: Longitude (decimal degrees).

    Returns:
        WeatherData with current conditions and today's forecast.

    Raises:
        requests.HTTPError: If the API returns an error status.
        KeyError: If the response structure is unexpected.
    """
    global _cached_data, _last_modified

    # Read cache under lock
    with _cache_lock:
        local_cached_data = _cached_data
        local_last_modified = _last_modified

    headers: dict[str, str] = {"User-Agent": WEATHER_USER_AGENT}
    if local_last_modified and local_cached_data:
        headers["If-Modified-Since"] = local_last_modified

    response = requests.get(
        WEATHER_API_URL,
        params={"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"},
        headers=headers,
        timeout=10,
    )

    if response.status_code == 304 and local_cached_data:
        # Data unchanged, parse from cache
        data = local_cached_data
    else:
        response.raise_for_status()
        data = response.json()
        # Write cache under lock
        with _cache_lock:
            _cached_data = data
            _last_modified = response.headers.get("Last-Modified")

    timeseries = data["properties"]["timeseries"]
    current = _parse_current(timeseries)
    high, low = _parse_high_low(timeseries)

    return WeatherData(
        temperature=current["temperature"],
        symbol_code=current["symbol_code"],
        high_temp=high,
        low_temp=low,
        precipitation_mm=current["precipitation_mm"],
        is_day=current["is_day"],
        wind_speed=current["wind_speed"],
        wind_from_direction=current["wind_from_direction"],
    )


def fetch_weather_safe(lat: float, lon: float) -> WeatherData | None:
    """Fetch weather, returning WeatherData or None on failure.

    Wraps fetch_weather() with error handling so API failures never
    crash the caller.

    Args:
        lat: Latitude (decimal degrees).
        lon: Longitude (decimal degrees).

    Returns:
        WeatherData on success, None on any failure.
    """
    try:
        return fetch_weather(lat, lon)
    except Exception:
        logger.exception("Failed to fetch weather for lat=%s lon=%s", lat, lon)
        return None
