"""Sun position provider using the astral library.

Computes sunrise, sunset, civil dawn, and civil dusk times for a given
location and date. Caches results per-day since sun times only change
once per calendar day.
"""

import logging
from datetime import date, datetime, timezone
from functools import lru_cache

from astral import Observer
from astral.sun import dawn, dusk, sunrise, sunset

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def get_sun_times(lat: float, lon: float, d: date) -> dict[str, datetime]:
    """Compute sunrise, sunset, dawn, and dusk for a location and date.

    Results are cached per (lat, lon, date) tuple since sun times only
    change once per calendar day. Thread-safe via CPython's GIL.

    Args:
        lat: Latitude in decimal degrees (positive = north).
        lon: Longitude in decimal degrees (positive = east).
        d: Date to compute sun times for.

    Returns:
        Dictionary with keys "dawn", "sunrise", "sunset", "dusk",
        each mapping to a timezone-aware UTC datetime.
    """
    observer = Observer(latitude=lat, longitude=lon)
    try:
        times = {
            "dawn": dawn(observer, date=d, tzinfo=timezone.utc),
            "sunrise": sunrise(observer, date=d, tzinfo=timezone.utc),
            "sunset": sunset(observer, date=d, tzinfo=timezone.utc),
            "dusk": dusk(observer, date=d, tzinfo=timezone.utc),
        }
    except ValueError:
        # Polar night or midnight sun — astral can't compute dawn/dusk.
        # Detect which case: try noon sun elevation.
        from astral.sun import elevation
        noon = datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc)
        elev = elevation(observer, noon)
        if elev > 0:
            # Midnight sun — sun never sets, always light
            logger.debug("Midnight sun at %.1f,%.1f on %s — treating as always light", lat, lon, d)
            times = {
                "dawn": datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc),
                "sunrise": datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc),
                "sunset": datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc),
                "dusk": datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc),
            }
        else:
            # Polar night — sun never rises, always dark
            logger.debug("Polar night at %.1f,%.1f on %s — treating as always dark", lat, lon, d)
            times = {
                "dawn": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "sunrise": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "sunset": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "dusk": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
            }

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
