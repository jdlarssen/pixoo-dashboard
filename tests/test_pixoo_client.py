"""Tests for PixooClient device communication error handling.

Verifies that push_frame() and set_brightness() catch network errors
(ReadTimeout, ConnectionError, etc.) and log warnings instead of
crashing the process.
"""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from requests.exceptions import ConnectionError, ReadTimeout

from src.device.pixoo_client import PixooClient, _ERROR_COOLDOWN_BASE, _ERROR_COOLDOWN_MAX


@pytest.fixture
def client():
    """Create a PixooClient with a mocked Pixoo instance."""
    with patch("src.device.pixoo_client.PixooClient.__init__", lambda self, *a, **kw: None):
        c = object.__new__(PixooClient)
        c._pixoo = MagicMock()
        c._size = 64
        c._last_push_time = 0.0
        c._error_until = 0.0
        c._ip = "192.168.0.193"
        c._current_cooldown = _ERROR_COOLDOWN_BASE
        return c


@pytest.fixture
def test_image():
    """Create a 64x64 test image."""
    return Image.new("RGB", (64, 64), color=(255, 0, 0))


class TestPushFrameErrorHandling:
    """push_frame() should catch network errors and not crash."""

    def test_push_frame_succeeds_normally(self, client, test_image):
        """Normal push_frame should work without error."""
        client.push_frame(test_image)
        client._pixoo.draw_image.assert_called_once_with(test_image)
        client._pixoo.push.assert_called_once()

    def test_push_frame_catches_read_timeout(self, client, test_image, caplog):
        """ReadTimeout from pixoo.push() should be caught and logged, not raised."""
        client._pixoo.push.side_effect = ReadTimeout("Read timed out")

        # Should NOT raise
        client.push_frame(test_image)

        assert "Device communication error" in caplog.text
        assert "ReadTimeout" in caplog.text or "Read timed out" in caplog.text

    def test_push_frame_catches_connection_error(self, client, test_image, caplog):
        """ConnectionError from pixoo.push() should be caught and logged, not raised."""
        client._pixoo.push.side_effect = ConnectionError("Connection refused")

        # Should NOT raise
        client.push_frame(test_image)

        assert "Device communication error" in caplog.text

    def test_push_frame_catches_draw_image_error(self, client, test_image, caplog):
        """Network error during draw_image should also be caught."""
        client._pixoo.draw_image.side_effect = ConnectionError("Connection reset")

        # Should NOT raise
        client.push_frame(test_image)

        assert "Device communication error" in caplog.text

    def test_push_frame_catches_oserror(self, client, test_image, caplog):
        """OSError (e.g., network unreachable) should be caught."""
        client._pixoo.push.side_effect = OSError("Network is unreachable")

        # Should NOT raise
        client.push_frame(test_image)

        assert "Device communication error" in caplog.text

    def test_push_frame_does_not_update_last_push_time_on_error(self, client, test_image):
        """When push fails, _last_push_time should not be updated."""
        client._last_push_time = 0.0
        client._pixoo.push.side_effect = ReadTimeout("Read timed out")

        client.push_frame(test_image)

        # last_push_time should still be 0.0 (not updated on failure)
        assert client._last_push_time == 0.0

    def test_push_frame_recovers_after_error(self, client, test_image):
        """After a network error and cooldown, the next push should succeed."""
        # First call fails
        client._pixoo.push.side_effect = ReadTimeout("Read timed out")
        client.push_frame(test_image)

        # Clear cooldown so second call is allowed immediately
        client._error_until = 0.0
        client._last_push_time = 0.0

        # Second call succeeds
        client._pixoo.push.side_effect = None
        client._pixoo.push.reset_mock()
        client._pixoo.draw_image.reset_mock()
        client.push_frame(test_image)

        client._pixoo.draw_image.assert_called_once_with(test_image)
        client._pixoo.push.assert_called_once()
        assert client._last_push_time > 0.0

    def test_push_frame_skipped_during_cooldown(self, client, test_image):
        """During error cooldown, push_frame should skip without calling device."""
        import time

        # Set cooldown far in the future
        client._error_until = time.monotonic() + 60

        client.push_frame(test_image)

        # Should not have called device at all
        client._pixoo.draw_image.assert_not_called()
        client._pixoo.push.assert_not_called()

    def test_push_frame_rate_limited(self, client, test_image):
        """Calls within the minimum push interval should be silently skipped."""
        import time

        # Simulate a recent push
        client._last_push_time = time.monotonic()

        client.push_frame(test_image)

        # Should not have called device due to rate limiting
        client._pixoo.draw_image.assert_not_called()
        client._pixoo.push.assert_not_called()


class TestPushFrameReturnValue:
    """push_frame() returns True/False/None to indicate success/error/skipped."""

    def test_returns_true_on_success(self, client, test_image):
        """Successful push returns True."""
        result = client.push_frame(test_image)
        assert result is True

    def test_returns_false_on_network_error(self, client, test_image):
        """Network error during push returns False (not None)."""
        client._pixoo.push.side_effect = ReadTimeout("Read timed out")
        result = client.push_frame(test_image)
        assert result is False

    def test_returns_false_on_oserror(self, client, test_image):
        """OSError (host down) returns False."""
        client._pixoo.push.side_effect = OSError("Host is down")
        result = client.push_frame(test_image)
        assert result is False

    def test_returns_none_during_cooldown(self, client, test_image):
        """Cooldown skip returns None (not False)."""
        import time

        client._error_until = time.monotonic() + 60
        result = client.push_frame(test_image)
        assert result is None

    def test_returns_none_when_rate_limited(self, client, test_image):
        """Rate-limit skip returns None (not False)."""
        import time

        client._last_push_time = time.monotonic()
        result = client.push_frame(test_image)
        assert result is None

    def test_caller_can_distinguish_error_from_skip(self, client, test_image):
        """Callers can use 'is True/False/None' to route health tracking."""
        import time

        # Success case
        result = client.push_frame(test_image)
        assert result is True

        # Error case
        client._last_push_time = 0.0
        client._error_until = 0.0
        client._pixoo.push.side_effect = ConnectionError("refused")
        result = client.push_frame(test_image)
        assert result is False

        # Skip case (cooldown from the error above)
        result = client.push_frame(test_image)
        assert result is None


class TestSetBrightnessErrorHandling:
    """set_brightness() should catch network errors and not crash."""

    def test_set_brightness_succeeds_normally(self, client):
        """Normal set_brightness should work without error."""
        client.set_brightness(50)
        client._pixoo.set_brightness.assert_called_once_with(50)

    def test_set_brightness_catches_read_timeout(self, client, caplog):
        """ReadTimeout from set_brightness should be caught and logged."""
        client._pixoo.set_brightness.side_effect = ReadTimeout("Read timed out")

        # Should NOT raise
        client.set_brightness(50)

        assert "Device communication error" in caplog.text

    def test_set_brightness_catches_connection_error(self, client, caplog):
        """ConnectionError from set_brightness should be caught and logged."""
        client._pixoo.set_brightness.side_effect = ConnectionError("Connection refused")

        # Should NOT raise
        client.set_brightness(50)

        assert "Device communication error" in caplog.text

    def test_set_brightness_catches_oserror(self, client, caplog):
        """OSError from set_brightness should be caught."""
        client._pixoo.set_brightness.side_effect = OSError("Network unreachable")

        # Should NOT raise
        client.set_brightness(50)

        assert "Device communication error" in caplog.text

    def test_set_brightness_still_caps_at_max(self, client):
        """Brightness capping logic should still work (before network call)."""
        client.set_brightness(100)
        # MAX_BRIGHTNESS is 90, so it should be capped
        client._pixoo.set_brightness.assert_called_once_with(90)


class TestPing:
    """ping() sends a lightweight health check to keep the device's WiFi alive."""

    def test_ping_returns_true_on_success(self, client):
        """Successful ping returns True."""
        client._pixoo.validate_connection.return_value = True
        assert client.ping() is True

    def test_ping_returns_false_on_network_error(self, client):
        """Network error during ping returns False."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        assert client.ping() is False

    def test_ping_returns_false_on_oserror(self, client):
        """OSError (host down) during ping returns False."""
        client._pixoo.validate_connection.side_effect = OSError("Host is down")
        assert client.ping() is False

    def test_ping_returns_none_during_cooldown(self, client):
        """Ping is skipped during error cooldown."""
        import time
        client._error_until = time.monotonic() + 60
        assert client.ping() is None
        client._pixoo.validate_connection.assert_not_called()

    def test_ping_sets_cooldown_on_failure(self, client):
        """Failed ping activates error cooldown."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        client.ping()
        assert client._error_until > 0


class TestReboot:
    """reboot() sends Device/SysReboot to force the device to restart."""

    def test_reboot_returns_true_on_success(self, client):
        """Successful reboot command returns True."""
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert client.reboot() is True

    def test_reboot_returns_false_on_network_error(self, client):
        """Network error during reboot returns False."""
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.side_effect = ConnectionError("Host is down")
            assert client.reboot() is False

    def test_reboot_returns_false_on_timeout(self, client):
        """Timeout during reboot returns False (device may already be rebooting)."""
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.side_effect = ReadTimeout("Read timed out")
            assert client.reboot() is False

    def test_reboot_sends_correct_command(self, client):
        """Reboot sends Device/SysReboot to http://{ip}/post."""
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            client.reboot()
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "192.168.0.193" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["Command"] == "Device/SysReboot"
            assert call_args[1]["timeout"] == 5


class TestExponentialBackoff:
    """Exponential backoff: cooldown doubles on consecutive failures, resets on success."""

    def test_first_failure_uses_base_cooldown(self, client, test_image):
        """After one push_frame failure, cooldown is set ~3s from now and doubles for next."""
        import time

        client._last_push_time = 0.0
        client._error_until = 0.0
        client._pixoo.push.side_effect = ConnectionError("refused")

        before = time.monotonic()
        client.push_frame(test_image)
        after = time.monotonic()

        # _error_until should be ~3s from now (base cooldown)
        assert client._error_until >= before + _ERROR_COOLDOWN_BASE
        assert client._error_until <= after + _ERROR_COOLDOWN_BASE + 0.1
        # _current_cooldown doubled for next failure
        assert client._current_cooldown == 6.0

    def test_consecutive_failures_double_cooldown(self, client, test_image):
        """Each consecutive failure doubles the cooldown: 3->6->12->24->48."""
        client._pixoo.push.side_effect = ConnectionError("refused")
        expected_after = [6.0, 12.0, 24.0, 48.0]

        for expected in expected_after:
            client._error_until = 0.0
            client._last_push_time = 0.0
            client.push_frame(test_image)
            assert client._current_cooldown == expected, (
                f"Expected {expected}, got {client._current_cooldown}"
            )

    def test_cooldown_caps_at_max(self, client, test_image):
        """Cooldown should never exceed _ERROR_COOLDOWN_MAX (60s)."""
        client._pixoo.push.side_effect = ConnectionError("refused")
        client._current_cooldown = 48.0

        # First failure: 48 -> should cap at 60 (not 96)
        client._error_until = 0.0
        client._last_push_time = 0.0
        client.push_frame(test_image)
        assert client._current_cooldown == 60.0

        # Second failure at cap: should stay at 60
        client._error_until = 0.0
        client._last_push_time = 0.0
        client.push_frame(test_image)
        assert client._current_cooldown == 60.0

    def test_success_resets_cooldown_to_base(self, client, test_image):
        """Successful push_frame resets cooldown back to base (3s)."""
        client._current_cooldown = 24.0  # simulating prior failures
        client._error_until = 0.0
        client._last_push_time = 0.0

        result = client.push_frame(test_image)
        assert result is True
        assert client._current_cooldown == _ERROR_COOLDOWN_BASE

    def test_ping_failure_also_increases_backoff(self, client):
        """Ping failure should also double the cooldown."""
        client._error_until = 0.0
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")

        client.ping()
        assert client._current_cooldown == 6.0

    def test_ping_success_resets_backoff(self, client):
        """Successful ping resets cooldown to base."""
        client._current_cooldown = 24.0
        client._error_until = 0.0
        client._pixoo.validate_connection.return_value = True

        result = client.ping()
        assert result is True
        assert client._current_cooldown == _ERROR_COOLDOWN_BASE

    def test_backoff_shared_between_push_and_ping(self, client, test_image):
        """Push and ping share the same backoff state."""
        # Push fails -> cooldown doubles to 6
        client._pixoo.push.side_effect = ConnectionError("refused")
        client._error_until = 0.0
        client._last_push_time = 0.0
        client.push_frame(test_image)
        assert client._current_cooldown == 6.0

        # Ping fails -> cooldown doubles to 12
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        client._error_until = 0.0
        client.ping()
        assert client._current_cooldown == 12.0
