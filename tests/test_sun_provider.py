"""Tests for the sun provider (sunrise/sunset/twilight calculation)."""

from datetime import date, datetime, timezone

from src.providers.sun import get_sun_times, is_dark


class TestGetSunTimes:
    """Verify sun time calculation for known locations and dates."""

    def test_oslo_winter_solstice(self):
        """Oslo Dec 21: sunrise ~09:18, sunset ~15:12 UTC."""
        times = get_sun_times(59.91, 10.75, date(2026, 12, 21))
        # Dawn should be before sunrise
        assert times["dawn"] < times["sunrise"]
        # Sunset should be before dusk
        assert times["sunset"] < times["dusk"]
        # Winter: sunrise after 08:00 UTC, sunset before 16:00 UTC
        assert times["sunrise"].hour >= 8
        assert times["sunset"].hour <= 15

    def test_oslo_summer_solstice(self):
        """Oslo Jun 21: sunrise ~01:53, sunset ~20:43 UTC."""
        times = get_sun_times(59.91, 10.75, date(2026, 6, 21))
        # Summer: sunrise before 03:00 UTC, sunset after 20:00 UTC
        assert times["sunrise"].hour <= 3
        assert times["sunset"].hour >= 20

    def test_caches_per_day(self):
        """Calling twice with same date should return same object (cached)."""
        t1 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        t2 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        assert t1 is t2

    def test_different_dates_not_cached(self):
        """Different dates should produce different results."""
        t1 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        t2 = get_sun_times(59.91, 10.75, date(2026, 6, 15))
        assert t1 is not t2


class TestIsDark:
    """Verify is_dark returns correct day/night status."""

    def test_midnight_is_dark(self):
        """Midnight in Oslo in March should be dark."""
        dt = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True

    def test_noon_is_light(self):
        """Noon in Oslo in March should be light."""
        dt = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is False

    def test_uses_dusk_not_sunset(self):
        """After geometric sunset but before civil dusk should still be light.

        In Oslo on March 15, sunset is ~17:10 UTC, dusk ~17:55 UTC.
        At 17:30 UTC it's past sunset but before dusk -- should NOT be dark.
        """
        dt = datetime(2026, 3, 15, 17, 30, tzinfo=timezone.utc)
        result = is_dark(dt, 59.91, 10.75)
        # Between sunset and dusk = still light (civil twilight)
        assert result is False

    def test_after_dusk_is_dark(self):
        """Well after dusk should be dark."""
        dt = datetime(2026, 3, 15, 20, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True

    def test_before_dawn_is_dark(self):
        """Before dawn should be dark."""
        dt = datetime(2026, 3, 15, 4, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True
