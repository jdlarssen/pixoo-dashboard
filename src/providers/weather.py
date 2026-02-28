"""Weather provider using the MET Norway Locationforecast 2.0 API.

Fetches current weather conditions, today's high/low temperatures, and
precipitation data for a given location. Uses If-Modified-Since caching
to respect MET API terms of service.
"""

import enum
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from src.config import WEATHER_API_URL, WEATHER_USER_AGENT

_CACHE_MAX_AGE = 3600  # discard If-Modified-Since after 1 hour

logger = logging.getLogger(__name__)


class CacheOutcome(enum.Enum):
    """Outcome of a cache lookup via get_or_claim."""

    FRESH = "fresh"  # Cache is valid; use cached data directly
    CLAIMED = "claimed"  # Stale/empty; caller should fetch and owns the lock
    BUSY = "busy"  # Another thread is already fetching


@dataclass
class CacheResult:
    """Result of WeatherCache.get_or_claim()."""

    outcome: CacheOutcome
    data: dict | None = None
    last_modified: str | None = None


class WeatherCache:
    """Thread-safe cache for MET API responses using If-Modified-Since."""

    def __init__(self, max_age: float = _CACHE_MAX_AGE) -> None:
        self._data: dict | None = None
        self._last_modified: str | None = None
        self._cache_time: float = 0.0
        self._lock = threading.Lock()
        self._max_age = max_age
        self._fetching = False

    def get(self) -> tuple[dict | None, str | None]:
        """Return (cached_data, last_modified) if cache is fresh, else (None, None).

        If another thread is already fetching, returns stale data to avoid
        thundering herd against the MET API.
        """
        with self._lock:
            if self._data and (time.monotonic() - self._cache_time) < self._max_age:
                return self._data, self._last_modified
            if self._fetching and self._data:
                return self._data, self._last_modified
            return None, None

    def mark_fetching(self) -> bool:
        """Mark cache as being refreshed. Returns True if caller should fetch."""
        with self._lock:
            if self._fetching:
                return False
            self._fetching = True
            return True

    def set(self, data: dict, last_modified: str | None) -> None:
        """Store response data and last-modified header."""
        with self._lock:
            self._data = data
            self._last_modified = last_modified
            self._cache_time = time.monotonic()
            self._fetching = False

    def get_or_claim(self) -> CacheResult:
        """Atomically check cache and claim fetch ownership if stale.

        Combines get() + mark_fetching() into a single lock acquisition,
        eliminating the TOCTOU race where last_modified could be lost.

        Returns:
            CacheResult with outcome FRESH (use data), CLAIMED (caller
            should fetch; includes last_modified for If-Modified-Since),
            or BUSY (another thread is fetching; stale data if available).
        """
        with self._lock:
            is_fresh = self._data and (time.monotonic() - self._cache_time) < self._max_age
            if is_fresh:
                return CacheResult(
                    outcome=CacheOutcome.FRESH,
                    data=self._data,
                    last_modified=self._last_modified,
                )
            if self._fetching:
                # Another thread is fetching; return stale data if available
                return CacheResult(
                    outcome=CacheOutcome.BUSY,
                    data=self._data,
                    last_modified=self._last_modified,
                )
            # Claim fetch ownership
            self._fetching = True
            return CacheResult(
                outcome=CacheOutcome.CLAIMED,
                data=self._data,
                last_modified=self._last_modified,
            )

    def clear_fetching(self) -> None:
        """Clear fetching flag on error (so next caller retries)."""
        with self._lock:
            self._fetching = False


# Module-level default instance for backward compat
_default_cache = WeatherCache()


@dataclass
class WeatherData:
    """Current weather conditions from MET Locationforecast 2.0."""

    temperature: float  # current temp in Celsius
    symbol_code: str  # MET symbol code, e.g. "partlycloudy_day"
    high_temp: float  # today's forecast high
    low_temp: float  # today's forecast low
    precipitation_mm: float  # next 1h precipitation amount in mm
    is_day: bool  # derived from symbol_code suffix
    wind_speed: float = 0.0  # wind speed in m/s
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
        raise ValueError("Missing 'air_temperature' in weather response instant details")

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
    today_str = datetime.now(ZoneInfo("Europe/Oslo")).date().isoformat()
    temps = []
    for entry in timeseries:
        time_val = entry.get("time", "")
        if not time_val.startswith(today_str):
            continue
        temp = entry.get("data", {}).get("instant", {}).get("details", {}).get("air_temperature")
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
    current_temp = first.get("instant", {}).get("details", {}).get("air_temperature")
    if current_temp is not None:
        return (current_temp, current_temp)

    return (0.0, 0.0)


def fetch_weather(
    lat: float,
    lon: float,
    cache: WeatherCache | None = None,
) -> WeatherData | None:
    """Fetch current weather from MET Locationforecast 2.0.

    Uses If-Modified-Since caching to avoid redundant downloads.
    MET API updates roughly every 10 minutes.

    Args:
        lat: Latitude (decimal degrees).
        lon: Longitude (decimal degrees).
        cache: Optional WeatherCache instance. Uses module-level default if None.

    Returns:
        WeatherData with current conditions and today's forecast.

    Raises:
        requests.HTTPError: If the API returns an error status.
        KeyError: If the response structure is unexpected.
    """
    cache = cache or _default_cache
    result = cache.get_or_claim()

    if result.outcome is CacheOutcome.FRESH:
        data = result.data
    elif result.outcome is CacheOutcome.BUSY:
        if result.data:
            data = result.data
        else:
            return None
    else:
        # CLAIMED — caller owns the fetch
        try:
            headers: dict[str, str] = {"User-Agent": WEATHER_USER_AGENT}
            if result.last_modified:
                headers["If-Modified-Since"] = result.last_modified

            response = requests.get(
                WEATHER_API_URL,
                params={"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"},
                headers=headers,
                timeout=10,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning("Rate-limited by API, backing off %ds", retry_after)
                time.sleep(min(retry_after, 30))  # Cap at 30s to avoid excessive waits
                cache.clear_fetching()
                return None

            if response.status_code == 304 and result.data:
                # Data unchanged, parse from cache
                data = result.data
                cache.clear_fetching()
            else:
                response.raise_for_status()
                data = response.json()
                cache.set(data, response.headers.get("Last-Modified"))
        except Exception:
            cache.clear_fetching()
            raise

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
    except (requests.RequestException, OSError, KeyError, ValueError) as exc:
        logger.warning("Failed to fetch weather for lat=%s lon=%s: %s", lat, lon, exc)
        return None
