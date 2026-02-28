"""Tests for the StalenessTracker class."""

from unittest.mock import patch

from src.providers.weather import WeatherData
from src.staleness import StalenessTracker


def _make_weather(**overrides) -> WeatherData:
    """Create a WeatherData with sensible defaults."""
    defaults = dict(
        temperature=20.0,
        high_temp=25.0,
        low_temp=15.0,
        is_day=True,
        symbol_code="clearsky_day",
        precipitation_mm=0.0,
    )
    defaults.update(overrides)
    return WeatherData(**defaults)


class TestBusStaleness:
    """Tests for bus data staleness tracking."""

    def test_initial_state_is_stale(self):
        st = StalenessTracker()
        data, is_stale, is_too_old = st.get_effective_bus()
        assert data == (None, None)
        assert is_stale is True
        assert is_too_old is True

    def test_fresh_data_not_stale(self):
        st = StalenessTracker()
        st.update_bus(([5, 10], [3, 7]))
        data, is_stale, is_too_old = st.get_effective_bus()
        assert data == ([5, 10], [3, 7])
        assert is_stale is False
        assert is_too_old is False

    def test_partial_update_preserves_other_direction(self):
        st = StalenessTracker()
        st.update_bus(([5, 10], [3, 7]))
        st.update_bus(([2, 8], None))  # dir2 failed
        assert st.last_good_bus == ([2, 8], [3, 7])

    def test_bus_data_age_zero_when_never_fetched(self):
        st = StalenessTracker()
        assert st.bus_data_age == 0.0

    def test_bus_becomes_stale_over_time(self):
        st = StalenessTracker()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_bus(([5], [3]))

            # Advance past stale threshold (default 180s)
            mono.return_value = base + 200
            _, is_stale, is_too_old = st.get_effective_bus()
            assert is_stale is True
            assert is_too_old is False
        finally:
            mock_time.stop()

    def test_bus_becomes_too_old(self):
        st = StalenessTracker()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_bus(([5], [3]))

            # Advance past too-old threshold (default 600s)
            mono.return_value = base + 700
            data, is_stale, is_too_old = st.get_effective_bus()
            assert is_stale is True
            assert is_too_old is True
            assert data == (None, None)
        finally:
            mock_time.stop()

    def test_per_direction_staleness(self):
        st = StalenessTracker()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_bus(([5], [3]))

            # Only update dir1 later
            mono.return_value = base + 100
            st.update_bus(([2], None))

            # At base+250: dir1 is 150s old (fresh), dir2 is 250s old (stale)
            mono.return_value = base + 250
            _, is_stale, _ = st.get_effective_bus()
            assert is_stale is True  # worst-case of both directions
        finally:
            mock_time.stop()


class TestWeatherStaleness:
    """Tests for weather data staleness tracking."""

    def test_initial_state_not_stale(self):
        st = StalenessTracker()
        data, is_stale, is_too_old = st.get_effective_weather()
        assert data is None
        assert is_stale is False
        assert is_too_old is False

    def test_fresh_weather_not_stale(self):
        st = StalenessTracker()
        wd = _make_weather()
        st.update_weather(wd)
        data, is_stale, is_too_old = st.get_effective_weather()
        assert data is wd
        assert is_stale is False
        assert is_too_old is False

    def test_weather_data_age_zero_when_never_fetched(self):
        st = StalenessTracker()
        assert st.weather_data_age == 0.0

    def test_weather_becomes_stale_over_time(self):
        st = StalenessTracker()
        wd = _make_weather()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_weather(wd)

            # Advance past stale threshold (1800s)
            mono.return_value = base + 1900
            data, is_stale, is_too_old = st.get_effective_weather()
            assert data is wd
            assert is_stale is True
            assert is_too_old is False
        finally:
            mock_time.stop()

    def test_weather_becomes_too_old(self):
        st = StalenessTracker()
        wd = _make_weather()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_weather(wd)

            # Advance past too-old threshold (3600s)
            mono.return_value = base + 3700
            data, is_stale, is_too_old = st.get_effective_weather()
            assert data is None
            assert is_stale is True
            assert is_too_old is True
        finally:
            mock_time.stop()

    def test_weather_update_refreshes_timestamp(self):
        st = StalenessTracker()
        base = 1000.0
        mock_time = patch("src.staleness.time.monotonic")
        mono = mock_time.start()
        try:
            mono.return_value = base
            st.update_weather(_make_weather(temperature=10))

            mono.return_value = base + 500
            st.update_weather(_make_weather(temperature=20))

            # 100s after second update = 600s after first, but only 100s fresh
            mono.return_value = base + 600
            data, is_stale, is_too_old = st.get_effective_weather()
            assert data.temperature == 20
            assert is_stale is False
        finally:
            mock_time.stop()
