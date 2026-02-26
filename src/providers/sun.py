"""Sun position provider using the astral library.

Computes sunrise, sunset, civil dawn, and civil dusk times for a given
location and date. Caches results per-day since sun times only change
once per calendar day.
"""

import threading
from datetime import date, datetime, timezone

from astral import Observer
from astral.sun import dawn, dusk, sunrise, sunset


# Cache: (lat, lon, date) -> sun times dict
_cache_key: tuple[float, float, date] | None = None
_cache_value: dict[str, datetime] | None = None
_cache_lock = threading.Lock()


def get_sun_times(lat: float, lon: float, d: date) -> dict[str, datetime]:
    """Compute sunrise, sunset, dawn, and dusk for a location and date.

    Results are cached per (lat, lon, date) tuple since sun times only
    change once per calendar day.

    Args:
        lat: Latitude in decimal degrees (positive = north).
        lon: Longitude in decimal degrees (positive = east).
        d: Date to compute sun times for.

    Returns:
        Dictionary with keys "dawn", "sunrise", "sunset", "dusk",
        each mapping to a timezone-aware UTC datetime.
    """
    global _cache_key, _cache_value

    key = (lat, lon, d)

    # Read cache under lock
    with _cache_lock:
        if _cache_key == key and _cache_value is not None:
            return _cache_value

    # Compute outside lock
    observer = Observer(latitude=lat, longitude=lon)
    times = {
        "dawn": dawn(observer, date=d, tzinfo=timezone.utc),
        "sunrise": sunrise(observer, date=d, tzinfo=timezone.utc),
        "sunset": sunset(observer, date=d, tzinfo=timezone.utc),
        "dusk": dusk(observer, date=d, tzinfo=timezone.utc),
    }

    # Write cache under lock
    with _cache_lock:
        _cache_key = key
        _cache_value = times

    return times


def is_dark(dt: datetime, lat: float, lon: float) -> bool:
    """Check if it's dark at the given time and location.

    Uses civil twilight boundaries (dawn/dusk) rather than geometric
    sunrise/sunset, giving a ~30-minute buffer after sunset where
    there's still usable light.

    Args:
        dt: Timezone-aware datetime to check.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        True if the time is before civil dawn or after civil dusk.
    """
    times = get_sun_times(lat, lon, dt.date())
    return dt < times["dawn"] or dt > times["dusk"]
