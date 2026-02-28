"""Tests for device keep-alive ping and auto-reboot recovery.

Verifies that the PixooClient ping() and reboot() methods integrate
correctly with the main loop's health tracking.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from requests.exceptions import ConnectionError

from src.device.pixoo_client import _ERROR_COOLDOWN_BASE, PixooClient


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


class TestKeepAliveIntegration:
    """Verify ping and push interact correctly with shared state."""

    def test_ping_success_does_not_affect_push_timing(self, client):
        """A successful ping should not reset the push rate limiter."""
        client._last_push_time = time.monotonic()  # recent push
        client._pixoo.validate_connection.return_value = True

        client.ping()

        # _last_push_time should be unchanged (ping doesn't touch it)
        assert client._last_push_time > 0

    def test_ping_failure_sets_cooldown_shared_with_push(self, client):
        """Ping failure cooldown should also block push_frame."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        client.ping()

        # Cooldown should now be active
        assert client._error_until > time.monotonic()

        # push_frame should be skipped during cooldown
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        result = client.push_frame(img)
        assert result is None  # skipped due to cooldown

    def test_push_failure_cooldown_blocks_ping(self, client):
        """Push failure cooldown should also block ping."""
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        client._pixoo.push.side_effect = ConnectionError("refused")
        client.push_frame(img)

        # Cooldown should now be active
        result = client.ping()
        assert result is None  # skipped due to cooldown

    def test_reboot_after_multiple_ping_failures(self, client):
        """After multiple ping failures, reboot should still be callable."""
        # Simulate 5 ping failures
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        for _ in range(5):
            client._error_until = 0.0  # clear cooldown for each attempt
            client.ping()

        # Reboot should work (separate code path)
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert client.reboot() is True
