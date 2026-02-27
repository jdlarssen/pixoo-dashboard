"""Tests for the internal watchdog thread that detects hung main loops."""

import threading
import time
from unittest.mock import patch

from src.main import Heartbeat, _watchdog_thread


class TestWatchdog:
    """Verify the watchdog fires on stale heartbeats and respects fresh ones."""

    def test_fresh_heartbeat_does_not_trigger(self):
        """Watchdog should not fire when heartbeat is continuously updated."""
        heartbeat = Heartbeat()
        exit_called = threading.Event()

        with patch("src.main.os._exit", side_effect=lambda code: exit_called.set()), \
             patch("src.main.os.kill"):
            t = threading.Thread(
                target=_watchdog_thread, args=(heartbeat, 0.3), daemon=True
            )
            t.start()

            # Keep heartbeat fresh for longer than the timeout
            for _ in range(5):
                time.sleep(0.1)
                heartbeat.beat()

        assert not exit_called.is_set(), "Watchdog should not fire with fresh heartbeat"

    def test_stale_heartbeat_triggers_exit(self):
        """Watchdog should call os._exit(1) when heartbeat goes stale."""
        heartbeat = Heartbeat()
        # Make the heartbeat stale by setting a very old timestamp
        heartbeat._timestamp = time.monotonic() - 10
        exit_code = []

        class _WatchdogFired(Exception):
            pass

        def mock_exit(code):
            exit_code.append(code)
            raise _WatchdogFired

        with patch("src.main.os._exit", side_effect=mock_exit), \
             patch("src.main.os.kill"), \
             patch("src.main.time.sleep", return_value=None):
            try:
                _watchdog_thread(heartbeat, timeout=0.1)
            except _WatchdogFired:
                pass

        assert exit_code == [1], "Watchdog should exit with code 1"

    def test_watchdog_thread_is_daemon(self):
        """Watchdog thread must be a daemon so it won't prevent clean shutdown."""
        heartbeat = Heartbeat()
        t = threading.Thread(
            target=_watchdog_thread, args=(heartbeat,), daemon=True
        )
        assert t.daemon is True
