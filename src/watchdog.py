"""Watchdog thread for detecting hung main loops.

Monitors a heartbeat timestamp and force-kills the process if the
main loop stops updating it, allowing launchd to restart the service.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time

logger = logging.getLogger(__name__)


class Heartbeat:
    """Thread-safe monotonic timestamp for watchdog heartbeat."""

    def __init__(self) -> None:
        self._timestamp = time.monotonic()

    def beat(self) -> None:
        """Record a heartbeat from the main loop."""
        self._timestamp = time.monotonic()

    @property
    def elapsed(self) -> float:
        """Seconds since last heartbeat."""
        return time.monotonic() - self._timestamp


def watchdog_thread(
    heartbeat: Heartbeat,
    timeout: float = 120,
    stop_event: threading.Event | None = None,
) -> None:
    """Monitor main loop heartbeat; force-kill if stale.

    Runs as a daemon thread. Checks every 30s whether the main loop
    has updated its heartbeat timestamp. If the heartbeat is older than
    *timeout* seconds, logs a critical message and calls os._exit(1)
    so launchd can restart the process.

    If *stop_event* is provided and set, the watchdog exits cleanly.
    """
    while not (stop_event and stop_event.is_set()):
        if stop_event:
            stop_event.wait(timeout=30)
            if stop_event.is_set():
                break
        else:
            time.sleep(30)
        elapsed = heartbeat.elapsed
        if elapsed > timeout:
            logger.critical(
                "Watchdog: main loop hung for %.0fs (threshold %ds), sending SIGTERM",
                elapsed,
                timeout,
            )
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(10)
            logger.critical("Watchdog: still alive after SIGTERM grace period, forcing exit")
            logging.shutdown()  # flush all handlers before hard exit
            os._exit(1)
    logger.info("Watchdog stopped cleanly")
