"""Tests for the weather provider and DisplayState weather integration."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.providers.weather import (
    WeatherData,
    _parse_current,
    _parse_high_low,
    _parse_is_day,
    fetch_weather,
    fetch_weather_safe,
)
from src.display.state import DisplayState


# ---------------------------------------------------------------------------
# Fixtures: mock MET API timeseries data
# ---------------------------------------------------------------------------

def _make_entry(time_str: str, temp: float, symbol: str = "cloudy",
                precip: float = 0.0, high6h: float | None = None,
                low6h: float | None = None,
                wind_speed: float = 3.0, wind_direction: float = 180.0) -> dict:
    """Build a single MET API timeseries entry for testing."""
    entry: dict = {
        "time": time_str,
        "data": {
            "instant": {
                "details": {
                    "air_temperature": temp,
                    "wind_speed": wind_speed,
                    "wind_from_direction": wind_direction,
                }
            },
            "next_1_hours": {
                "summary": {"symbol_code": symbol},
                "details": {"precipitation_amount": precip},
            },
        },
    }
    if high6h is not None or low6h is not None:
        entry["data"]["next_6_hours"] = {
            "details": {
                "air_temperature_max": high6h if high6h is not None else 0.0,
                "air_temperature_min": low6h if low6h is not None else 0.0,
            }
        }
    return entry


def _today_str() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Tests: _parse_is_day
# ---------------------------------------------------------------------------

class TestParseIsDay:
    def test_day_suffix(self):
        assert _parse_is_day("clearsky_day") is True

    def test_night_suffix(self):
        assert _parse_is_day("rain_night") is False

    def test_polartwilight_suffix(self):
        assert _parse_is_day("snow_polartwilight") is False

    def test_no_suffix(self):
        """Codes without suffix (e.g. 'cloudy', 'fog') are treated as day."""
        assert _parse_is_day("cloudy") is True
        assert _parse_is_day("fog") is True
        assert _parse_is_day("rain") is True


# ---------------------------------------------------------------------------
# Tests: _parse_current
# ---------------------------------------------------------------------------

class TestParseCurrent:
    def test_basic_parse(self):
        ts = [_make_entry(f"{_today_str()}T12:00:00Z", 5.2, "partlycloudy_day", 0.3)]
        result = _parse_current(ts)
        assert result["temperature"] == 5.2
        assert result["symbol_code"] == "partlycloudy_day"
        assert result["precipitation_mm"] == 0.3
        assert result["is_day"] is True

    def test_night_symbol(self):
        ts = [_make_entry(f"{_today_str()}T23:00:00Z", -2.0, "clearsky_night", 0.0)]
        result = _parse_current(ts)
        assert result["symbol_code"] == "clearsky_night"
        assert result["is_day"] is False

    def test_missing_next_1_hours(self):
        """If next_1_hours is absent, defaults to cloudy and 0 precip."""
        entry = {
            "time": f"{_today_str()}T12:00:00Z",
            "data": {
                "instant": {"details": {"air_temperature": 3.0}},
            },
        }
        result = _parse_current([entry])
        assert result["symbol_code"] == "cloudy"
        assert result["precipitation_mm"] == 0.0


# ---------------------------------------------------------------------------
# Tests: _parse_high_low
# ---------------------------------------------------------------------------

class TestParseHighLow:
    def test_multiple_today_entries(self):
        today = _today_str()
        ts = [
            _make_entry(f"{today}T06:00:00Z", 2.0),
            _make_entry(f"{today}T12:00:00Z", 8.5),
            _make_entry(f"{today}T18:00:00Z", 5.0),
            _make_entry(f"{today}T23:00:00Z", 1.5),
        ]
        high, low = _parse_high_low(ts)
        assert high == 8.5
        assert low == 1.5

    def test_single_entry(self):
        today = _today_str()
        ts = [_make_entry(f"{today}T12:00:00Z", 4.0)]
        high, low = _parse_high_low(ts)
        assert high == 4.0
        assert low == 4.0

    def test_fallback_next_6_hours(self):
        """When no today entries, use next_6_hours from first entry."""
        ts = [_make_entry("2099-01-01T12:00:00Z", 3.0, high6h=10.0, low6h=-1.0)]
        high, low = _parse_high_low(ts)
        assert high == 10.0
        assert low == -1.0

    def test_negative_temperatures(self):
        today = _today_str()
        ts = [
            _make_entry(f"{today}T06:00:00Z", -5.0),
            _make_entry(f"{today}T12:00:00Z", -2.0),
            _make_entry(f"{today}T18:00:00Z", -8.0),
        ]
        high, low = _parse_high_low(ts)
        assert high == -2.0
        assert low == -8.0


# ---------------------------------------------------------------------------
# Tests: fetch_weather_safe
# ---------------------------------------------------------------------------

class TestFetchWeatherSafe:
    @patch("src.providers.weather.requests.get")
    def test_returns_none_on_network_error(self, mock_get):
        mock_get.side_effect = ConnectionError("No network")
        result = fetch_weather_safe(63.0, 10.0)
        assert result is None

    @patch("src.providers.weather.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response
        result = fetch_weather_safe(63.0, 10.0)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: If-Modified-Since caching
# ---------------------------------------------------------------------------

class TestCaching:
    @patch("src.providers.weather.requests.get")
    def test_304_returns_cached_data(self, mock_get):
        """When API returns 304, parse from cached data."""
        from src.providers.weather import WeatherCache

        today = _today_str()
        cached_json = {
            "properties": {
                "timeseries": [
                    _make_entry(f"{today}T12:00:00Z", 7.0, "fair_day", 0.0),
                ]
            }
        }
        cache = WeatherCache()
        cache.set(cached_json, "Thu, 20 Feb 2026 12:00:00 GMT")

        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response

        result = fetch_weather(63.0, 10.0, cache=cache)
        assert result.temperature == 7.0
        assert result.symbol_code == "fair_day"

    @patch("src.providers.weather.requests.get")
    def test_200_updates_cache(self, mock_get):
        """When API returns 200, update cache and parse."""
        from src.providers.weather import WeatherCache

        today = _today_str()
        response_json = {
            "properties": {
                "timeseries": [
                    _make_entry(f"{today}T12:00:00Z", 3.5, "rain", 1.2),
                ]
            }
        }
        cache = WeatherCache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_json
        mock_response.headers = {"Last-Modified": "Thu, 20 Feb 2026 13:00:00 GMT"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_weather(63.0, 10.0, cache=cache)
        assert result.temperature == 3.5
        assert result.precipitation_mm == 1.2
        cached_data, last_mod = cache.get()
        assert last_mod == "Thu, 20 Feb 2026 13:00:00 GMT"


# ---------------------------------------------------------------------------
# Tests: DisplayState weather integration
# ---------------------------------------------------------------------------

class TestDisplayStateWeather:
    def test_default_weather_fields(self):
        """Weather fields default to None/True when no data provided."""
        state = DisplayState(time_str="14:30", date_str="tor 20. feb")
        assert state.weather_temp is None
        assert state.weather_symbol is None
        assert state.weather_high is None
        assert state.weather_low is None
        assert state.weather_precip_mm is None
        assert state.weather_is_day is True

    def test_from_now_without_weather(self):
        dt = datetime(2026, 2, 20, 14, 30)
        state = DisplayState.from_now(dt)
        assert state.weather_temp is None
        assert state.weather_symbol is None

    def test_from_now_with_weather_data(self):
        dt = datetime(2026, 2, 20, 14, 30)
        wd = WeatherData(
            temperature=5.7,
            symbol_code="partlycloudy_day",
            high_temp=8.3,
            low_temp=1.2,
            precipitation_mm=0.5,
            is_day=True,
        )
        state = DisplayState.from_now(dt, weather_data=wd)
        assert state.weather_temp == 6  # rounded
        assert state.weather_symbol == "partlycloudy_day"
        assert state.weather_high == 8   # rounded
        assert state.weather_low == 1    # rounded
        assert state.weather_precip_mm == 0.5
        assert state.weather_is_day is True

    def test_equality_with_weather(self):
        """DisplayState equality works with weather fields (dirty flag)."""
        wd = WeatherData(
            temperature=5.0, symbol_code="rain", high_temp=8.0,
            low_temp=1.0, precipitation_mm=1.0, is_day=True,
        )
        dt = datetime(2026, 2, 20, 14, 30)
        s1 = DisplayState.from_now(dt, weather_data=wd)
        s2 = DisplayState.from_now(dt, weather_data=wd)
        assert s1 == s2

    def test_inequality_on_temp_change(self):
        """Different temperatures produce different states."""
        dt = datetime(2026, 2, 20, 14, 30)
        wd1 = WeatherData(
            temperature=5.0, symbol_code="rain", high_temp=8.0,
            low_temp=1.0, precipitation_mm=1.0, is_day=True,
        )
        wd2 = WeatherData(
            temperature=6.0, symbol_code="rain", high_temp=8.0,
            low_temp=1.0, precipitation_mm=1.0, is_day=True,
        )
        s1 = DisplayState.from_now(dt, weather_data=wd1)
        s2 = DisplayState.from_now(dt, weather_data=wd2)
        assert s1 != s2

    def test_negative_temp_rounds_correctly(self):
        dt = datetime(2026, 2, 20, 14, 30)
        wd = WeatherData(
            temperature=-3.7, symbol_code="snow_night", high_temp=-1.2,
            low_temp=-5.8, precipitation_mm=0.0, is_day=False,
        )
        state = DisplayState.from_now(dt, weather_data=wd)
        assert state.weather_temp == -4  # round(-3.7) = -4
        assert state.weather_high == -1  # round(-1.2) = -1
        assert state.weather_low == -6   # round(-5.8) = -6
        assert state.weather_is_day is False


# ---------------------------------------------------------------------------
# Tests: Wind data extraction
# ---------------------------------------------------------------------------

class TestWindData:
    def test_parse_current_includes_wind(self):
        ts = [_make_entry(f"{_today_str()}T12:00:00Z", 5.0, "rain_day", 2.0,
                          wind_speed=8.5, wind_direction=270.0)]
        result = _parse_current(ts)
        assert result["wind_speed"] == 8.5
        assert result["wind_from_direction"] == 270.0

    def test_weather_data_has_wind_fields(self):
        wd = WeatherData(
            temperature=5.0, symbol_code="rain_day", high_temp=8.0,
            low_temp=1.0, precipitation_mm=2.0, is_day=True,
            wind_speed=8.5, wind_from_direction=270.0,
        )
        assert wd.wind_speed == 8.5
        assert wd.wind_from_direction == 270.0

    def test_wind_defaults_to_zero(self):
        """Wind fields should default to 0 when not provided."""
        wd = WeatherData(
            temperature=5.0, symbol_code="rain", high_temp=8.0,
            low_temp=1.0, precipitation_mm=0.0, is_day=True,
        )
        assert wd.wind_speed == 0.0
        assert wd.wind_from_direction == 0.0
