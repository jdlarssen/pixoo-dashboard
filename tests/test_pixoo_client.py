"""Tests for PixooClient device communication error handling.

Verifies that push_frame() and set_brightness() catch network errors
(ReadTimeout, ConnectionError, etc.) and log warnings instead of
crashing the process.
"""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from requests.exceptions import ConnectionError, ReadTimeout

from src.device.pixoo_client import PixooClient


@pytest.fixture
def client():
    """Create a PixooClient with a mocked Pixoo instance."""
    with patch("src.device.pixoo_client.PixooClient.__init__", lambda self, *a, **kw: None):
        c = object.__new__(PixooClient)
        c._pixoo = MagicMock()
        c._size = 64
        c._last_push_time = 0.0
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
        """After a network error, the next push should succeed normally."""
        # First call fails
        client._pixoo.push.side_effect = ReadTimeout("Read timed out")
        client.push_frame(test_image)

        # Second call succeeds
        client._pixoo.push.side_effect = None
        client._pixoo.push.reset_mock()
        client._pixoo.draw_image.reset_mock()
        client.push_frame(test_image)

        client._pixoo.draw_image.assert_called_once_with(test_image)
        client._pixoo.push.assert_called_once()
        assert client._last_push_time > 0.0


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
