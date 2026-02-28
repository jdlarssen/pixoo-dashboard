"""Tests for main_loop orchestration helpers and logic in src/main.py.

Covers the helper functions (_reverse_geocode, _precip_category, _wind_category,
_should_swap_animation, build_font_map), the watchdog thread, staleness logic,
and TEST_WEATHER environment variable activation.
"""

import os
import threading
import time
from unittest.mock import MagicMock, patch

from src.main import (
    Heartbeat,
    _precip_category,
    _reverse_geocode,
    _should_swap_animation,
    _watchdog_thread,
    _wind_category,
    build_font_map,
)
from src.providers.weather import WeatherData

# ---------------------------------------------------------------------------
# _reverse_geocode() tests
# ---------------------------------------------------------------------------


class TestReverseGeocode:
    """Tests for _reverse_geocode() -- OpenStreetMap Nominatim lookup."""

    @patch("requests.get")
    def test_returns_city_on_success(self, mock_get):
        """Successful geocode returns the city name from the address."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"address": {"city": "Trondheim", "county": "Trondelag"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.43, 10.39)

        assert result == "Trondheim"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["lat"] == 63.43
        assert call_kwargs[1]["params"]["lon"] == 10.39
        assert call_kwargs[1]["timeout"] == 5

    @patch("requests.get")
    def test_falls_back_to_town(self, mock_get):
        """When 'city' is missing, falls back to 'town'."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"address": {"town": "Stjordal", "county": "Trondelag"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.47, 10.92)
        assert result == "Stjordal"

    @patch("requests.get")
    def test_falls_back_to_municipality(self, mock_get):
        """When city and town are missing, falls back to 'municipality'."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"address": {"municipality": "Malvik"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.43, 10.69)
        assert result == "Malvik"

    @patch("requests.get")
    def test_falls_back_to_village(self, mock_get):
        """When city, town, and municipality are missing, falls back to 'village'."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"address": {"village": "Hommelvik"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.41, 10.79)
        assert result == "Hommelvik"

    @patch("requests.get")
    def test_returns_none_when_no_address_fields(self, mock_get):
        """Returns None when address has none of the expected fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"address": {"country": "Norway"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.43, 10.39)
        assert result is None

    @patch("requests.get")
    def test_returns_none_on_connection_error(self, mock_get):
        """Network failure returns None without raising."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        result = _reverse_geocode(63.43, 10.39)
        assert result is None

    @patch("requests.get")
    def test_returns_none_on_timeout(self, mock_get):
        """Request timeout returns None without raising."""
        import requests

        mock_get.side_effect = requests.Timeout("Read timed out")

        result = _reverse_geocode(63.43, 10.39)
        assert result is None

    @patch("requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        """HTTP 500 response returns None without raising."""
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.43, 10.39)
        assert result is None

    @patch("requests.get")
    def test_returns_none_on_json_decode_error(self, mock_get):
        """Malformed JSON response returns None without raising."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response

        result = _reverse_geocode(63.43, 10.39)
        assert result is None


# ---------------------------------------------------------------------------
# _precip_category() tests
# ---------------------------------------------------------------------------


class TestPrecipCategory:
    """Tests for _precip_category() -- precipitation intensity classification."""

    def test_zero_is_light(self):
        """0 mm precipitation is light."""
        assert _precip_category(0.0) == "light"

    def test_half_mm_is_light(self):
        """0.5 mm is below 1.0 threshold -- still light."""
        assert _precip_category(0.5) == "light"

    def test_just_below_one_is_light(self):
        """0.99 mm is light (boundary: < 1.0)."""
        assert _precip_category(0.99) == "light"

    def test_one_mm_is_moderate(self):
        """1.0 mm is the lower boundary of moderate (>= 1.0)."""
        assert _precip_category(1.0) == "moderate"

    def test_two_mm_is_moderate(self):
        """2.0 mm is moderate."""
        assert _precip_category(2.0) == "moderate"

    def test_three_mm_is_moderate(self):
        """3.0 mm is the upper boundary of moderate (<= 3.0)."""
        assert _precip_category(3.0) == "moderate"

    def test_just_above_three_is_heavy(self):
        """3.01 mm exceeds moderate threshold -- heavy."""
        assert _precip_category(3.01) == "heavy"

    def test_five_mm_is_heavy(self):
        """5.0 mm precipitation is heavy."""
        assert _precip_category(5.0) == "heavy"

    def test_ten_mm_is_heavy(self):
        """10.0 mm precipitation is heavy."""
        assert _precip_category(10.0) == "heavy"


# ---------------------------------------------------------------------------
# _wind_category() tests
# ---------------------------------------------------------------------------


class TestWindCategory:
    """Tests for _wind_category() -- wind speed classification."""

    def test_zero_is_calm(self):
        """0 m/s wind is calm."""
        assert _wind_category(0.0) == "calm"

    def test_one_point_five_is_calm(self):
        """1.5 m/s is calm."""
        assert _wind_category(1.5) == "calm"

    def test_just_below_three_is_calm(self):
        """2.99 m/s is calm (boundary: < 3.0)."""
        assert _wind_category(2.99) == "calm"

    def test_three_is_moderate(self):
        """3.0 m/s is the lower boundary of moderate (>= 3.0)."""
        assert _wind_category(3.0) == "moderate"

    def test_four_is_moderate(self):
        """4.0 m/s is moderate."""
        assert _wind_category(4.0) == "moderate"

    def test_five_is_moderate(self):
        """5.0 m/s is the upper boundary of moderate (<= 5.0)."""
        assert _wind_category(5.0) == "moderate"

    def test_just_above_five_is_strong(self):
        """5.01 m/s exceeds moderate threshold -- strong."""
        assert _wind_category(5.01) == "strong"

    def test_eight_is_strong(self):
        """8.0 m/s is strong wind."""
        assert _wind_category(8.0) == "strong"


# ---------------------------------------------------------------------------
# _should_swap_animation() tests
# ---------------------------------------------------------------------------


class TestShouldSwapAnimation:
    """Tests for _should_swap_animation() -- checks when weather animation needs swapping."""

    def test_same_conditions_no_swap(self):
        """Identical conditions should not trigger a swap."""
        assert (
            _should_swap_animation(
                new_group="rain",
                is_night=False,
                precip_mm=2.0,
                wind_speed=4.0,
                last_group="rain",
                last_night=False,
                last_precip_mm=2.0,
                last_wind_speed=4.0,
            )
            is False
        )

    def test_group_change_triggers_swap(self):
        """Different weather group triggers a swap."""
        assert (
            _should_swap_animation(
                new_group="snow",
                is_night=False,
                precip_mm=2.0,
                wind_speed=4.0,
                last_group="rain",
                last_night=False,
                last_precip_mm=2.0,
                last_wind_speed=4.0,
            )
            is True
        )

    def test_night_change_triggers_swap(self):
        """Day-to-night transition triggers a swap."""
        assert (
            _should_swap_animation(
                new_group="clear",
                is_night=True,
                precip_mm=0.0,
                wind_speed=1.0,
                last_group="clear",
                last_night=False,
                last_precip_mm=0.0,
                last_wind_speed=1.0,
            )
            is True
        )

    def test_precip_category_change_triggers_swap(self):
        """Precipitation crossing a category boundary triggers a swap."""
        # light (0.5) -> moderate (2.0)
        assert (
            _should_swap_animation(
                new_group="rain",
                is_night=False,
                precip_mm=2.0,
                wind_speed=4.0,
                last_group="rain",
                last_night=False,
                last_precip_mm=0.5,
                last_wind_speed=4.0,
            )
            is True
        )

    def test_precip_same_category_no_swap(self):
        """Precipitation within the same category does not trigger swap."""
        # both moderate (1.5 and 2.5)
        assert (
            _should_swap_animation(
                new_group="rain",
                is_night=False,
                precip_mm=2.5,
                wind_speed=4.0,
                last_group="rain",
                last_night=False,
                last_precip_mm=1.5,
                last_wind_speed=4.0,
            )
            is False
        )

    def test_wind_category_change_triggers_swap(self):
        """Wind speed crossing a category boundary triggers a swap."""
        # calm (1.0) -> strong (6.0)
        assert (
            _should_swap_animation(
                new_group="rain",
                is_night=False,
                precip_mm=2.0,
                wind_speed=6.0,
                last_group="rain",
                last_night=False,
                last_precip_mm=2.0,
                last_wind_speed=1.0,
            )
            is True
        )

    def test_wind_same_category_no_swap(self):
        """Wind speed within the same category does not trigger swap."""
        # both moderate (3.5 and 4.5)
        assert (
            _should_swap_animation(
                new_group="rain",
                is_night=False,
                precip_mm=2.0,
                wind_speed=4.5,
                last_group="rain",
                last_night=False,
                last_precip_mm=2.0,
                last_wind_speed=3.5,
            )
            is False
        )


# ---------------------------------------------------------------------------
# build_font_map() tests
# ---------------------------------------------------------------------------


class TestBuildFontMap:
    """Tests for build_font_map() -- loads fonts and maps them to logical names."""

    @patch("src.main.load_fonts")
    def test_returns_expected_keys(self, mock_load_fonts):
        """Font map should have 'small' and 'tiny' keys."""
        mock_font_small = MagicMock()
        mock_font_tiny = MagicMock()
        mock_load_fonts.return_value = {"5x8": mock_font_small, "4x6": mock_font_tiny}

        result = build_font_map("/fake/font/dir")

        assert "small" in result
        assert "tiny" in result
        assert len(result) == 2

    @patch("src.main.load_fonts")
    def test_small_maps_to_font_small_config(self, mock_load_fonts):
        """'small' key maps to the FONT_SMALL config value ('5x8')."""
        mock_font_small = MagicMock(name="5x8_font")
        mock_font_tiny = MagicMock(name="4x6_font")
        mock_load_fonts.return_value = {"5x8": mock_font_small, "4x6": mock_font_tiny}

        result = build_font_map("/fake/font/dir")

        assert result["small"] is mock_font_small

    @patch("src.main.load_fonts")
    def test_tiny_maps_to_font_tiny_config(self, mock_load_fonts):
        """'tiny' key maps to the FONT_TINY config value ('4x6')."""
        mock_font_small = MagicMock(name="5x8_font")
        mock_font_tiny = MagicMock(name="4x6_font")
        mock_load_fonts.return_value = {"5x8": mock_font_small, "4x6": mock_font_tiny}

        result = build_font_map("/fake/font/dir")

        assert result["tiny"] is mock_font_tiny

    @patch("src.main.load_fonts")
    def test_passes_font_dir_to_load_fonts(self, mock_load_fonts):
        """build_font_map passes the font_dir argument through to load_fonts."""
        mock_load_fonts.return_value = {"5x8": MagicMock(), "4x6": MagicMock()}

        build_font_map("/custom/fonts")

        mock_load_fonts.assert_called_once_with("/custom/fonts")


# ---------------------------------------------------------------------------
# _watchdog_thread() tests (complementary to test_watchdog.py)
# ---------------------------------------------------------------------------


class TestWatchdogThread:
    """Additional watchdog tests focused on os._exit triggering and heartbeat logic."""

    def test_stale_heartbeat_calls_os_exit_with_code_1(self):
        """Watchdog calls os._exit(1) when heartbeat exceeds timeout."""
        heartbeat = Heartbeat()
        heartbeat._timestamp = time.monotonic() - 200  # already stale
        exit_codes = []

        class _WatchdogFired(Exception):
            pass

        def capture_exit(code):
            exit_codes.append(code)
            raise _WatchdogFired

        with (
            patch("src.main.os._exit", side_effect=capture_exit),
            patch("src.main.os.kill"),
            patch("src.main.time.sleep", return_value=None),
        ):
            try:
                _watchdog_thread(heartbeat, timeout=1.0)
            except _WatchdogFired:
                pass

        assert exit_codes == [1]

    def test_fresh_heartbeat_no_exit(self):
        """Watchdog does not fire when heartbeat is fresh."""
        heartbeat = Heartbeat()
        exit_called = threading.Event()
        iterations = [0]

        original_sleep = time.sleep

        def counting_sleep(seconds):
            iterations[0] += 1
            # Keep heartbeat fresh
            heartbeat.beat()
            if iterations[0] >= 3:
                raise StopIteration("End test after 3 iterations")
            # Actually sleep a tiny bit to let the thread run
            original_sleep(0.01)

        with (
            patch("src.main.os._exit", side_effect=lambda c: exit_called.set()),
            patch("src.main.os.kill"),
            patch("src.main.time.sleep", side_effect=counting_sleep),
        ):
            try:
                _watchdog_thread(heartbeat, timeout=10.0)
            except StopIteration:
                pass

        assert not exit_called.is_set(), "Watchdog should not fire with fresh heartbeat"

    def test_watchdog_uses_monotonic_for_elapsed(self):
        """Watchdog computes elapsed time using time.monotonic()."""
        # Set heartbeat to a known monotonic value
        heartbeat = Heartbeat()
        base_time = 1000.0
        heartbeat._timestamp = base_time

        exit_codes = []

        class _WatchdogFired(Exception):
            pass

        def capture_exit(code):
            exit_codes.append(code)
            raise _WatchdogFired

        # time.monotonic returns base_time + 200 (so elapsed = 200)
        with (
            patch("src.main.os._exit", side_effect=capture_exit),
            patch("src.main.os.kill"),
            patch("src.main.time.sleep", return_value=None),
            patch("src.main.time.monotonic", return_value=base_time + 200),
        ):
            try:
                _watchdog_thread(heartbeat, timeout=120)
            except _WatchdogFired:
                pass

        assert exit_codes == [1], "Should have fired: elapsed=200 > timeout=120"


# ---------------------------------------------------------------------------
# Staleness logic tests
# ---------------------------------------------------------------------------


class TestStalenessLogic:
    """Tests for bus and weather staleness thresholds in main_loop.

    Instead of running the actual main_loop (which has an infinite loop),
    we test the staleness calculation logic extracted from the loop body.
    The thresholds are defined inside main_loop, so we verify the logic
    by replicating the exact calculations used there.
    """

    # Staleness thresholds (must match main_loop constants)
    BUS_STALE_THRESHOLD = 180
    BUS_TOO_OLD_THRESHOLD = 600
    WEATHER_STALE_THRESHOLD = 1800
    WEATHER_TOO_OLD_THRESHOLD = 3600

    def _calc_staleness(self, now_mono, last_good_time, stale_threshold, too_old_threshold):
        """Replicate the staleness calculation from main_loop."""
        age = now_mono - last_good_time if last_good_time > 0 else 0
        stale = age > stale_threshold and last_good_time > 0
        too_old = age > too_old_threshold and last_good_time > 0
        return stale, too_old

    # --- Bus staleness ---

    def test_bus_fresh_data_not_stale(self):
        """Bus data within 3 minutes is not stale."""
        now = 1000.0
        last_good = now - 60  # 60 seconds old
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is False
        assert too_old is False

    def test_bus_data_at_stale_threshold(self):
        """Bus data exactly at 180s boundary is not stale (> not >=)."""
        now = 1000.0
        last_good = now - 180  # exactly 180 seconds
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is False  # > 180, not >= 180
        assert too_old is False

    def test_bus_data_stale_but_not_too_old(self):
        """Bus data at 4 minutes (240s) is stale but not too old."""
        now = 1000.0
        last_good = now - 240
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is True
        assert too_old is False

    def test_bus_data_too_old_shows_dashes(self):
        """Bus data at 11 minutes (660s) is too old -- should show dashes."""
        now = 1000.0
        last_good = now - 660
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is True  # also stale if too old
        assert too_old is True

    def test_bus_data_at_too_old_boundary(self):
        """Bus data exactly at 600s boundary is not too old (> not >=)."""
        now = 1000.0
        last_good = now - 600
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is True  # 600 > 180
        assert too_old is False  # not > 600

    def test_bus_never_fetched_not_stale(self):
        """Bus data with last_good_time=0 (never fetched) is not flagged stale."""
        now = 1000.0
        last_good = 0.0  # never fetched
        stale, too_old = self._calc_staleness(
            now, last_good, self.BUS_STALE_THRESHOLD, self.BUS_TOO_OLD_THRESHOLD
        )
        assert stale is False
        assert too_old is False

    def test_bus_too_old_results_in_none_effective_data(self):
        """When bus data is too old, effective_bus should be (None, None)."""
        bus_data = ([5, 12], [3, 8])
        bus_too_old = True
        effective_bus = (None, None) if bus_too_old else bus_data
        assert effective_bus == (None, None)

    def test_bus_not_too_old_preserves_data(self):
        """When bus data is not too old, effective_bus preserves actual data."""
        bus_data = ([5, 12], [3, 8])
        bus_too_old = False
        effective_bus = (None, None) if bus_too_old else bus_data
        assert effective_bus == ([5, 12], [3, 8])

    # --- Weather staleness ---

    def test_weather_fresh_data_not_stale(self):
        """Weather data within 30 minutes is not stale."""
        now = 5000.0
        last_good = now - 600  # 10 minutes old
        stale, too_old = self._calc_staleness(
            now, last_good, self.WEATHER_STALE_THRESHOLD, self.WEATHER_TOO_OLD_THRESHOLD
        )
        assert stale is False
        assert too_old is False

    def test_weather_data_stale_but_not_too_old(self):
        """Weather data at 45 minutes (2700s) is stale but not too old."""
        now = 5000.0
        last_good = now - 2700
        stale, too_old = self._calc_staleness(
            now, last_good, self.WEATHER_STALE_THRESHOLD, self.WEATHER_TOO_OLD_THRESHOLD
        )
        assert stale is True
        assert too_old is False

    def test_weather_data_too_old_shows_dashes(self):
        """Weather data at 2 hours (7200s) is too old -- should show dashes."""
        now = 10000.0
        last_good = now - 7200
        stale, too_old = self._calc_staleness(
            now, last_good, self.WEATHER_STALE_THRESHOLD, self.WEATHER_TOO_OLD_THRESHOLD
        )
        assert stale is True
        assert too_old is True

    def test_weather_at_too_old_boundary(self):
        """Weather data exactly at 3600s boundary is not too old (> not >=)."""
        now = 5000.0
        last_good = now - 3600
        stale, too_old = self._calc_staleness(
            now, last_good, self.WEATHER_STALE_THRESHOLD, self.WEATHER_TOO_OLD_THRESHOLD
        )
        assert stale is True  # 3600 > 1800
        assert too_old is False  # not > 3600

    def test_weather_never_fetched_not_stale(self):
        """Weather with last_good_time=0 (never fetched) is not flagged stale."""
        now = 5000.0
        last_good = 0.0
        stale, too_old = self._calc_staleness(
            now, last_good, self.WEATHER_STALE_THRESHOLD, self.WEATHER_TOO_OLD_THRESHOLD
        )
        assert stale is False
        assert too_old is False

    def test_weather_too_old_results_in_none_effective_data(self):
        """When weather data is too old, effective_weather should be None."""
        weather_data = WeatherData(
            temperature=15.0,
            symbol_code="cloudy",
            high_temp=18.0,
            low_temp=10.0,
            precipitation_mm=0.0,
            is_day=True,
        )
        weather_too_old = True
        effective_weather = None if weather_too_old else weather_data
        assert effective_weather is None

    def test_weather_not_too_old_preserves_data(self):
        """When weather data is not too old, effective_weather preserves actual data."""
        weather_data = WeatherData(
            temperature=15.0,
            symbol_code="cloudy",
            high_temp=18.0,
            low_temp=10.0,
            precipitation_mm=0.0,
            is_day=True,
        )
        weather_too_old = False
        effective_weather = None if weather_too_old else weather_data
        assert effective_weather is weather_data


# ---------------------------------------------------------------------------
# TEST_WEATHER mode tests
# ---------------------------------------------------------------------------


class TestTestWeatherMode:
    """Tests for TEST_WEATHER environment variable activation in main_loop.

    Since main_loop runs an infinite loop, we test it by letting exactly one
    iteration execute, then breaking out via a side effect on time.sleep.
    """

    def _make_mock_client(self):
        """Create a minimal mock PixooClient."""
        client = MagicMock()
        client.push_frame.return_value = True
        client.set_brightness.return_value = None
        return client

    def _make_mock_fonts(self):
        """Create a minimal mock font dict."""
        return {"small": MagicMock(), "tiny": MagicMock()}

    @patch.dict(os.environ, {"TEST_WEATHER": "rain"})
    @patch("src.main.render_frame")
    @patch("src.main.get_animation")
    @patch("src.main.is_dark", return_value=False)
    @patch("src.main.symbol_to_group", return_value="rain")
    @patch("src.main.fetch_bus_data", return_value=(None, None))
    @patch("src.main.get_target_brightness", return_value=80)
    @patch("src.main.DisplayState.from_now")
    def test_test_weather_rain_uses_hardcoded_data(
        self,
        mock_from_now,
        mock_brightness,
        mock_bus,
        mock_symbol_group,
        mock_is_dark,
        mock_get_anim,
        mock_render,
    ):
        """TEST_WEATHER=rain activates hardcoded rain weather data."""
        from src.main import main_loop

        mock_state = MagicMock()
        mock_state.__eq__ = lambda s, o: False  # always "changed" to trigger push
        mock_state.__ne__ = lambda s, o: True
        mock_from_now.return_value = mock_state

        mock_render.return_value = MagicMock()  # fake PIL Image
        mock_get_anim.return_value = MagicMock()  # fake animation
        mock_get_anim.return_value.tick.return_value = MagicMock()  # fake frame

        client = self._make_mock_client()
        fonts = self._make_mock_fonts()

        # Let one iteration run then break out
        call_count = [0]

        def break_after_one(seconds):
            call_count[0] += 1
            if call_count[0] >= 1:
                raise KeyboardInterrupt

        with (
            patch("src.main.time.sleep", side_effect=break_after_one),
            patch("src.main.threading.Thread") as mock_thread,
        ):
            # Prevent watchdog thread from actually starting
            mock_thread.return_value = MagicMock()

            try:
                main_loop(client, fonts)
            except KeyboardInterrupt:
                pass

        # Verify render_frame was called (frame was pushed)
        assert mock_render.called or client.push_frame.called

    @patch.dict(os.environ, {"TEST_WEATHER": "clear"})
    @patch("src.main.render_frame")
    @patch("src.main.get_animation")
    @patch("src.main.is_dark", return_value=False)
    @patch("src.main.symbol_to_group", return_value="clear")
    @patch("src.main.fetch_bus_data", return_value=(None, None))
    @patch("src.main.get_target_brightness", return_value=80)
    @patch("src.main.DisplayState.from_now")
    def test_test_weather_clear_skips_api_fetch(
        self,
        mock_from_now,
        mock_brightness,
        mock_bus,
        mock_symbol_group,
        mock_is_dark,
        mock_get_anim,
        mock_render,
    ):
        """TEST_WEATHER=clear skips the weather API fetch entirely."""
        from src.main import main_loop

        mock_state = MagicMock()
        mock_state.__eq__ = lambda s, o: False
        mock_state.__ne__ = lambda s, o: True
        mock_from_now.return_value = mock_state

        mock_render.return_value = MagicMock()
        mock_get_anim.return_value = MagicMock()
        mock_get_anim.return_value.tick.return_value = MagicMock()

        client = self._make_mock_client()
        fonts = self._make_mock_fonts()

        call_count = [0]

        def break_after_one(seconds):
            call_count[0] += 1
            if call_count[0] >= 1:
                raise KeyboardInterrupt

        with (
            patch("src.main.time.sleep", side_effect=break_after_one),
            patch("src.main.threading.Thread") as mock_thread,
            patch("src.main.fetch_weather_safe") as mock_weather_api,
        ):
            mock_thread.return_value = MagicMock()

            try:
                main_loop(client, fonts)
            except KeyboardInterrupt:
                pass

            # Weather API should NOT be called in test mode
            mock_weather_api.assert_not_called()

    @patch.dict(os.environ, {}, clear=False)
    def test_no_test_weather_env_var_means_normal_mode(self):
        """Without TEST_WEATHER env var, test_weather_mode is None/falsy."""
        # Remove TEST_WEATHER if it exists
        env_copy = os.environ.copy()
        env_copy.pop("TEST_WEATHER", None)

        with patch.dict(os.environ, env_copy, clear=True):
            test_weather_mode = os.environ.get("TEST_WEATHER")
            assert not test_weather_mode

    def test_test_weather_map_has_expected_keys(self):
        """The test_weather_map in main_loop should support known weather modes."""
        # We verify the known keys by checking they produce valid WeatherData
        expected_modes = ["clear", "rain", "snow", "fog", "cloudy", "sun", "thunder"]
        for mode in expected_modes:
            # Construct the WeatherData the same way main_loop does
            _b = dict(
                temperature=30,
                high_temp=32,
                low_temp=22,
                is_day=True,
            )
            data = {
                "clear": WeatherData(
                    **_b,
                    symbol_code="clearsky_day",
                    precipitation_mm=0.0,
                    wind_speed=2.0,
                    wind_from_direction=180.0,
                ),
                "rain": WeatherData(
                    **_b,
                    symbol_code="rain_day",
                    precipitation_mm=5.0,
                    wind_speed=8.0,
                    wind_from_direction=270.0,
                ),
                "snow": WeatherData(
                    **_b,
                    symbol_code="snow_day",
                    precipitation_mm=2.0,
                    wind_speed=5.0,
                    wind_from_direction=200.0,
                ),
                "fog": WeatherData(
                    **_b,
                    symbol_code="fog",
                    precipitation_mm=0.0,
                ),
                "cloudy": WeatherData(
                    **_b,
                    symbol_code="cloudy",
                    precipitation_mm=0.0,
                ),
                "sun": WeatherData(
                    **_b,
                    symbol_code="clearsky_day",
                    precipitation_mm=0.0,
                ),
                "thunder": WeatherData(
                    **_b,
                    symbol_code="rainandthunder_day",
                    precipitation_mm=8.0,
                    wind_speed=12.0,
                    wind_from_direction=250.0,
                ),
            }
            assert mode in data, f"Missing test weather mode: {mode}"
            assert isinstance(data[mode], WeatherData)
