"""Device keep-alive ping and auto-reboot recovery logic.

Monitors consecutive device failures and triggers a reboot when the
failure count reaches a threshold. After reboot, enforces a recovery
wait period before resuming pings.
"""

from __future__ import annotations

import logging
import time

from src.config import (
    DEVICE_PING_INTERVAL,
    DEVICE_REBOOT_RECOVERY_WAIT,
    DEVICE_REBOOT_THRESHOLD,
)
from src.device.pixoo_client import PixooClient, PushResult
from src.providers.discord_monitor import HealthTracker

logger = logging.getLogger(__name__)


class DeviceKeepAlive:
    """Track device health and manage keep-alive pings + auto-reboot.

    The main loop calls :meth:`record_success` / :meth:`record_failure`
    after each frame push and :meth:`tick` once per iteration to handle
    background pings and reboot recovery.
    """

    def __init__(self) -> None:
        self.consecutive_failures: int = 0
        self.last_success_time: float = 0.0
        self._reboot_wait_until: float = 0.0

    def record_success(self) -> None:
        """Record a successful device communication (push or ping)."""
        self.last_success_time = time.monotonic()
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed device communication."""
        self.consecutive_failures += 1

    def tick(
        self,
        client: PixooClient,
        now_mono: float,
        health_tracker: HealthTracker | None = None,
    ) -> None:
        """Run one keep-alive cycle: check reboot threshold, then ping.

        Should be called once per main-loop iteration (roughly every 1s).

        Args:
            client: Pixoo device client for ping/reboot commands.
            now_mono: Current ``time.monotonic()`` value.
            health_tracker: Optional health tracker for monitoring integration.
        """
        if now_mono <= self._reboot_wait_until:
            return  # still in post-reboot recovery wait

        # Check if we should attempt a reboot
        if self.consecutive_failures >= DEVICE_REBOOT_THRESHOLD:
            logger.warning(
                "Device has %d consecutive failures, attempting reboot",
                self.consecutive_failures,
            )
            if client.reboot():
                self._reboot_wait_until = time.monotonic() + DEVICE_REBOOT_RECOVERY_WAIT
                logger.info(
                    "Waiting %ds for device to recover after reboot",
                    DEVICE_REBOOT_RECOVERY_WAIT,
                )
            else:
                wait = DEVICE_REBOOT_RECOVERY_WAIT * 2
                logger.warning("Reboot command failed, backing off for %ds", wait)
                self._reboot_wait_until = time.monotonic() + DEVICE_REBOOT_RECOVERY_WAIT * 2
            self.consecutive_failures = 0
            return

        # Keep-alive ping when no recent device success
        time_since = now_mono - self.last_success_time
        if time_since >= DEVICE_PING_INTERVAL and self.last_success_time > 0:
            ping_result = client.ping()
            if ping_result is PushResult.SUCCESS:
                self.record_success()
                if health_tracker:
                    health_tracker.record_success("device")
            elif ping_result is PushResult.ERROR:
                self.record_failure()
                if health_tracker:
                    health_tracker.record_failure("device", "Device ping failed")
