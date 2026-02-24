"""Tests for Discord monitoring module -- HealthTracker and embed builders."""

import time
from unittest.mock import patch

import discord

from src.providers.discord_monitor import (
    COLORS,
    HealthTracker,
    error_embed,
    recovery_embed,
    shutdown_embed,
    startup_embed,
    status_embed,
)


class TestEmbedBuilders:
    """Tests for color-coded embed builder functions."""

    def test_error_embed_has_red_color(self):
        """Error embed uses red color (0xFF0000)."""
        embed = error_embed("bus_api", "TimeoutError", "connect timed out", 120.0, "never")
        assert embed.color.value == 0xFF0000

    def test_error_embed_has_required_fields(self):
        """Error embed contains Component, Error Type, Failing For, Last Success fields."""
        embed = error_embed("bus_api", "TimeoutError", "connect timed out", 120.0, "2026-02-24 10:00 UTC")
        field_names = [f.name for f in embed.fields]
        assert "Component" in field_names
        assert "Error Type" in field_names
        assert "Failing For" in field_names
        assert "Last Success" in field_names

    def test_error_embed_field_values(self):
        """Error embed field values contain expected content."""
        embed = error_embed("weather_api", "HTTPError", "503 Service Unavailable", 300.0, "2026-02-24 10:00 UTC")
        fields = {f.name: f.value for f in embed.fields}
        assert fields["Component"] == "weather_api"
        assert fields["Error Type"] == "HTTPError"
        assert fields["Failing For"] == "300s"
        assert fields["Last Success"] == "2026-02-24 10:00 UTC"

    def test_error_embed_has_footer(self):
        """Error embed has Divoom Hub Monitor footer."""
        embed = error_embed("bus_api", "TimeoutError", "detail", 60.0, "never")
        assert embed.footer.text == "Divoom Hub Monitor"

    def test_recovery_embed_has_green_color(self):
        """Recovery embed uses green color (0x00FF00)."""
        embed = recovery_embed("bus_api", 1380.0)
        assert embed.color.value == 0x00FF00

    def test_recovery_embed_includes_downtime(self):
        """Recovery embed description mentions duration in minutes."""
        embed = recovery_embed("bus_api", 1380.0)
        assert "23 minutes" in embed.description

    def test_recovery_embed_has_downtime_field(self):
        """Recovery embed has a Downtime field."""
        embed = recovery_embed("weather_api", 600.0)
        field_names = [f.name for f in embed.fields]
        assert "Downtime" in field_names

    def test_startup_embed_has_blue_color(self):
        """Startup embed uses blue color (0x3498DB)."""
        embed = startup_embed("192.168.1.100", "NSR:123", "NSR:456", 63.43, 10.39)
        assert embed.color.value == 0x3498DB

    def test_startup_embed_has_config_fields(self):
        """Startup embed contains Pixoo IP, Bus Stops, and Weather Location fields."""
        embed = startup_embed("192.168.1.100", "NSR:123", "NSR:456", 63.43, 10.39)
        field_names = [f.name for f in embed.fields]
        assert "Pixoo IP" in field_names
        assert "Bus Stops" in field_names
        assert "Weather Location" in field_names

    def test_startup_embed_field_values(self):
        """Startup embed fields contain the config values."""
        embed = startup_embed("10.0.0.5", "Q1", "Q2", 59.91, 10.75)
        fields = {f.name: f.value for f in embed.fields}
        assert fields["Pixoo IP"] == "10.0.0.5"
        assert "Q1" in fields["Bus Stops"]
        assert "Q2" in fields["Bus Stops"]
        assert "59.91" in fields["Weather Location"]
        assert "10.75" in fields["Weather Location"]

    def test_startup_embed_title(self):
        """Startup embed has correct title."""
        embed = startup_embed("1.2.3.4", "A", "B", 0.0, 0.0)
        assert embed.title == "Divoom Hub Started"

    def test_shutdown_embed_has_gray_color(self):
        """Shutdown embed uses gray color (0x95A5A6)."""
        embed = shutdown_embed()
        assert embed.color.value == 0x95A5A6

    def test_shutdown_embed_title(self):
        """Shutdown embed has correct title."""
        embed = shutdown_embed()
        assert embed.title == "Divoom Hub Stopped"

    def test_status_embed_shows_component_status(self):
        """Status embed shows per-component status fields."""
        components = {
            "bus_api": {"status": "ok", "failure_count": 0, "last_success": "2026-02-24 10:00 UTC"},
            "weather_api": {"status": "down", "failure_count": 5, "downtime_s": 300.0, "last_success": "2026-02-24 09:30 UTC"},
        }
        embed = status_embed(components, 3600.0)
        field_names = [f.name for f in embed.fields]
        assert "bus_api" in field_names
        assert "weather_api" in field_names

    def test_status_embed_ok_component_shows_ok(self):
        """Status embed shows OK for healthy components."""
        components = {"bus_api": {"status": "ok", "failure_count": 0, "last_success": "now"}}
        embed = status_embed(components, 100.0)
        fields = {f.name: f.value for f in embed.fields}
        assert fields["bus_api"] == "OK"

    def test_status_embed_down_component_shows_down(self):
        """Status embed shows DOWN with duration for failing components."""
        components = {"device": {"status": "down", "failure_count": 10, "downtime_s": 120.0, "last_success": "ago"}}
        embed = status_embed(components, 100.0)
        fields = {f.name: f.value for f in embed.fields}
        assert "DOWN" in fields["device"]
        assert "120" in fields["device"]

    def test_status_embed_has_blue_color(self):
        """Status embed uses blue color."""
        embed = status_embed({}, 0.0)
        assert embed.color.value == 0x3498DB

    def test_status_embed_shows_uptime(self):
        """Status embed description includes uptime."""
        embed = status_embed({}, 7200.0)
        assert "2h" in embed.description

    def test_colors_dict_has_expected_keys(self):
        """COLORS dict has error, recovery, startup, shutdown keys."""
        assert "error" in COLORS
        assert "recovery" in COLORS
        assert "startup" in COLORS
        assert "shutdown" in COLORS


class TestHealthTracker:
    """Tests for HealthTracker debounce logic and recovery behavior.

    All tests use monitor=None so no Discord client is needed.
    """

    def test_single_failure_does_not_alert(self):
        """One failure for bus_api (threshold=3) does not trigger alerting."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("bus_api", "TimeoutError: connect timed out")
        state = tracker._components["bus_api"]
        assert state.is_alerting is False
        assert state.failure_count == 1

    def test_two_failures_below_threshold(self):
        """Two failures for bus_api (threshold=3) still not alerting."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        state = tracker._components["bus_api"]
        assert state.is_alerting is False
        assert state.failure_count == 2

    def test_debounce_threshold_triggers_alert(self):
        """Three failures for bus_api (threshold=3) triggers alerting."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        state = tracker._components["bus_api"]
        assert state.is_alerting is True
        assert state.failure_count == 3

    def test_weather_api_alerts_after_two_failures(self):
        """Weather API has threshold=2, so two failures trigger alert."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("weather_api", "HTTPError: 503")
        tracker.record_failure("weather_api", "HTTPError: 503")
        state = tracker._components["weather_api"]
        assert state.is_alerting is True

    def test_device_alerts_after_five_failures(self):
        """Device has threshold=5, so five failures trigger alert."""
        tracker = HealthTracker(monitor=None)
        for _ in range(4):
            tracker.record_failure("device", "OSError")
        assert tracker._components["device"].is_alerting is False
        tracker.record_failure("device", "OSError")
        assert tracker._components["device"].is_alerting is True

    def test_unknown_component_uses_default_threshold(self):
        """Unknown component uses default threshold of 3."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("custom_thing", "Error")
        tracker.record_failure("custom_thing", "Error")
        assert tracker._components["custom_thing"].is_alerting is False
        tracker.record_failure("custom_thing", "Error")
        assert tracker._components["custom_thing"].is_alerting is True

    def test_recovery_after_alert_clears_state(self):
        """Success after alerting clears failure state and is_alerting."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        assert tracker._components["bus_api"].is_alerting is True

        tracker.record_success("bus_api")
        state = tracker._components["bus_api"]
        assert state.is_alerting is False
        assert state.failure_count == 0
        assert state.first_failure_time == 0.0

    def test_success_without_prior_failure_is_noop(self):
        """record_success on unknown component creates state but doesn't crash."""
        tracker = HealthTracker(monitor=None)
        tracker.record_success("bus_api")
        # Should create the component with no failures
        assert "bus_api" in tracker._components
        state = tracker._components["bus_api"]
        assert state.failure_count == 0
        assert state.is_alerting is False

    def test_success_on_non_alerting_component(self):
        """record_success when not alerting just updates last_success."""
        tracker = HealthTracker(monitor=None)
        tracker.record_failure("bus_api", "TimeoutError")  # 1 failure, below threshold
        tracker.record_success("bus_api")
        state = tracker._components["bus_api"]
        assert state.failure_count == 0
        assert state.is_alerting is False

    def test_different_components_tracked_independently(self):
        """Failures on one component don't affect another."""
        tracker = HealthTracker(monitor=None)
        # bus_api: 3 failures -> alerting
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        # weather_api: 1 failure -> NOT alerting
        tracker.record_failure("weather_api", "HTTPError: 503")

        assert tracker._components["bus_api"].is_alerting is True
        assert tracker._components["weather_api"].is_alerting is False

    def test_get_status_returns_all_components(self):
        """get_status() returns correct structure for tracked components."""
        tracker = HealthTracker(monitor=None)
        tracker.record_success("bus_api")
        tracker.record_failure("weather_api", "HTTPError")
        tracker.record_failure("weather_api", "HTTPError")  # threshold=2 -> alerting

        status = tracker.get_status()
        assert "bus_api" in status
        assert "weather_api" in status
        assert status["bus_api"]["status"] == "ok"
        assert status["weather_api"]["status"] == "down"
        assert status["weather_api"]["failure_count"] == 2
        assert "downtime_s" in status["weather_api"]

    def test_get_status_empty_tracker(self):
        """get_status() returns empty dict when no components tracked."""
        tracker = HealthTracker(monitor=None)
        assert tracker.get_status() == {}

    def test_uptime_increases(self):
        """uptime_s property increases over time."""
        tracker = HealthTracker(monitor=None)
        time.sleep(0.05)  # 50ms
        assert tracker.uptime_s > 0

    def test_first_failure_records_time(self):
        """First failure sets first_failure_time."""
        tracker = HealthTracker(monitor=None)
        before = time.monotonic()
        tracker.record_failure("bus_api", "TimeoutError")
        after = time.monotonic()
        state = tracker._components["bus_api"]
        assert before <= state.first_failure_time <= after

    @patch("src.providers.discord_monitor.time.monotonic")
    def test_repeat_alert_after_interval(self, mock_monotonic):
        """After initial alert, repeat alert only after repeat_interval elapsed."""
        # bus_api: threshold=3, repeat_interval=900
        mock_monotonic.return_value = 1000.0

        tracker = HealthTracker(monitor=None)
        # Trigger initial alert
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        state = tracker._components["bus_api"]
        assert state.is_alerting is True
        initial_alert_time = state.last_alert_time

        # 4th failure immediately -- should NOT update last_alert_time
        mock_monotonic.return_value = 1001.0
        tracker.record_failure("bus_api", "TimeoutError")
        assert state.last_alert_time == initial_alert_time  # unchanged

        # After 900s interval, should send repeat alert
        mock_monotonic.return_value = 1000.0 + 900.0
        tracker.record_failure("bus_api", "TimeoutError")
        assert state.last_alert_time == 1900.0  # updated

    @patch("src.providers.discord_monitor.time.monotonic")
    def test_recovery_downtime_calculation(self, mock_monotonic):
        """Recovery correctly calculates downtime from first_failure_time."""
        mock_monotonic.return_value = 100.0
        tracker = HealthTracker(monitor=None)

        # Record failures
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        tracker.record_failure("bus_api", "TimeoutError")
        assert tracker._components["bus_api"].first_failure_time == 100.0

        # Recover 300s later
        mock_monotonic.return_value = 400.0
        tracker.record_success("bus_api")
        # State should be reset
        state = tracker._components["bus_api"]
        assert state.failure_count == 0
        assert state.is_alerting is False

    def test_last_success_str_updated_on_success(self):
        """record_success updates last_success_str with UTC timestamp."""
        tracker = HealthTracker(monitor=None)
        tracker.record_success("bus_api")
        state = tracker._components["bus_api"]
        assert "UTC" in state.last_success_str
        assert state.last_success_str != "never"
