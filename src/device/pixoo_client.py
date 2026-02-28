"""Pixoo 64 device communication wrapper with connection refresh and rate limiting.

The Pixoo 64 device has a documented limitation: its embedded HTTP server
cannot reliably handle more than ~1 request per second. Exceeding this rate
causes the device to drop connections and eventually freeze.

This wrapper enforces safe timing, adds timeouts to all device HTTP calls
(the upstream pixoo library uses none), and implements error cooldown to
prevent cascading failures when the device is in a degraded state.
"""

import enum
import logging
import time

import requests as _requests_module
from PIL import Image
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from src.config import (
    DEVICE_ERROR_COOLDOWN_BASE,
    DEVICE_ERROR_COOLDOWN_MAX,
    DEVICE_HTTP_TIMEOUT,
    DEVICE_MIN_PUSH_INTERVAL,
    DISPLAY_SIZE,
    MAX_BRIGHTNESS,
)

logger = logging.getLogger(__name__)


class PushResult(enum.Enum):
    """Outcome of a device communication attempt (push or ping)."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


# Backward-compatible aliases for tests and internal use
_DEVICE_TIMEOUT = DEVICE_HTTP_TIMEOUT
_MIN_PUSH_INTERVAL = DEVICE_MIN_PUSH_INTERVAL
_ERROR_COOLDOWN_BASE = DEVICE_ERROR_COOLDOWN_BASE
_ERROR_COOLDOWN_MAX = DEVICE_ERROR_COOLDOWN_MAX


class _TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that injects a default timeout on every request."""

    def __init__(self, timeout: float = _DEVICE_TIMEOUT, **kwargs):
        self._timeout = timeout
        super().__init__(**kwargs)

    def send(self, request, *, timeout=None, **kwargs):
        if timeout is None:
            timeout = self._timeout
        return super().send(request, timeout=timeout, **kwargs)


class _RequestsShim:
    """Drop-in replacement for the ``requests`` module used by pixoo.

    Routes ``post()`` through a :class:`requests.Session` configured with
    :class:`_TimeoutHTTPAdapter`, ensuring all device HTTP calls have a
    default timeout without monkey-patching ``requests.post``.
    """

    def __init__(self, timeout: float = _DEVICE_TIMEOUT):
        self._session = _requests_module.Session()
        adapter = _TimeoutHTTPAdapter(timeout=timeout)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def post(self, url, *args, **kwargs):
        return self._session.post(url, *args, **kwargs)

    def __getattr__(self, name):
        # Fall through to the real requests module for anything else
        return getattr(_requests_module, name)


class PixooClient:
    """Wrapper around the pixoo library's Pixoo class.

    Provides:
    - Safe rate limiting (minimum 1.0s between pushes, matching device capacity)
    - Timeout injection for all device HTTP calls (5s default)
    - Error cooldown to prevent cascading failures on degraded device
    - Connection refresh to prevent the ~300-push lockup (pixoo lib feature)
    - Brightness control capped at MAX_BRIGHTNESS (90%)
    - Simulator mode for development without hardware
    - Resilient error handling: network errors are logged, not raised
    """

    def __init__(self, ip: str, size: int = DISPLAY_SIZE, simulated: bool = False):
        """Initialize the Pixoo device connection.

        Args:
            ip: Device IP address on the local network.
            size: Display size in pixels (64 for Pixoo 64).
            simulated: If True, use the pixoo library's Tkinter simulator.
        """
        # Inject a Session-based shim into the pixoo module so that all
        # device HTTP calls go through _TimeoutHTTPAdapter (default timeout).
        import pixoo.objects.pixoo as _pixoo_module

        _pixoo_module.requests = _RequestsShim(timeout=_DEVICE_TIMEOUT)

        from pixoo import Pixoo

        kwargs = {
            "ip_address": ip,
            "size": size,
            "debug": False,
            "refresh_connection_automatically": True,
        }

        if simulated:
            from pixoo.configurations.simulatorconfiguration import SimulatorConfiguration

            kwargs["simulated"] = True
            kwargs["simulation_config"] = SimulatorConfiguration(scale=4)

        self._pixoo = Pixoo(**kwargs)
        self._size = size
        self._last_push_time: float = 0.0
        self._error_until: float = 0.0  # monotonic time when cooldown expires
        self._ip = ip
        self._current_cooldown: float = _ERROR_COOLDOWN_BASE

    def push_frame(self, image: Image.Image) -> PushResult:
        """Push a PIL Image frame to the device.

        Enforces a minimum 1.0-second interval between pushes. The Pixoo 64
        can only reliably handle ~1 push per second over HTTP. Calls arriving
        too soon are silently skipped (no warning spam at animation tick rate).

        After a communication error, a cooldown period prevents rapid retries
        that would further overwhelm the device.

        Network errors (timeouts, connection failures) are caught and logged
        so the main loop can continue and retry on the next iteration.

        Args:
            image: A PIL RGB Image (should be 64x64 for Pixoo 64).

        Returns:
            PushResult.SUCCESS if the frame was delivered to the device.
            PushResult.ERROR if a communication error occurred (device unreachable).
            PushResult.SKIPPED if the push was skipped (rate limit or error cooldown).
        """
        now = time.monotonic()

        # Respect error cooldown
        if now < self._error_until:
            return PushResult.SKIPPED

        # Rate limit: enforce minimum interval
        elapsed = now - self._last_push_time
        if self._last_push_time > 0 and elapsed < _MIN_PUSH_INTERVAL:
            return PushResult.SKIPPED

        try:
            self._pixoo.draw_image(image)
            self._pixoo.push()
        except (RequestException, OSError) as exc:
            logger.warning("Device communication error during push_frame: %s", exc)
            self._error_until = time.monotonic() + self._current_cooldown
            logger.info(
                "Device cooldown: pausing pushes for %.0fs (backoff)",
                self._current_cooldown,
            )
            self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
            return PushResult.ERROR
        self._current_cooldown = _ERROR_COOLDOWN_BASE
        self._last_push_time = time.monotonic()
        return PushResult.SUCCESS

    def ping(self) -> PushResult:
        """Send a lightweight health-check to keep the device WiFi alive.

        Uses Channel/GetAllConf which returns device config without any
        visual side-effect. Respects error cooldown.

        Returns:
            PushResult.SUCCESS if device responded, PushResult.ERROR on
            communication error, PushResult.SKIPPED if skipped (cooldown).
        """
        now = time.monotonic()
        if now < self._error_until:
            return PushResult.SKIPPED

        try:
            self._pixoo.validate_connection()
            self._current_cooldown = _ERROR_COOLDOWN_BASE
            return PushResult.SUCCESS
        except (RequestException, OSError) as exc:
            logger.warning("Device ping failed: %s", exc)
            self._error_until = time.monotonic() + self._current_cooldown
            self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
            return PushResult.ERROR

    def reboot(self) -> bool:
        """Send Device/SysReboot command to force the device to restart.

        Best-effort: the device may not respond if it's truly offline,
        or may disconnect mid-reboot. Either case returns False.

        Returns:
            True if the reboot command was acknowledged, False otherwise.
        """
        try:
            _requests_module.post(
                f"http://{self._ip}/post",
                json={"Command": "Device/SysReboot"},
                timeout=_DEVICE_TIMEOUT,
            )
            logger.warning("Device reboot command sent to %s", self._ip)
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device reboot failed: %s", exc)
            return False

    def set_brightness(self, level: int) -> None:
        """Set device brightness, capped at MAX_BRIGHTNESS.

        Network errors are caught and logged so the main loop can continue.

        Args:
            level: Brightness level (0-100). Will be capped at MAX_BRIGHTNESS (90).
        """
        capped = min(level, MAX_BRIGHTNESS)
        if level > MAX_BRIGHTNESS:
            logger.info(
                "Brightness %d exceeds max (%d), capping at %d", level, MAX_BRIGHTNESS, capped
            )
        try:
            self._pixoo.set_brightness(capped)
        except (RequestException, OSError) as exc:
            logger.warning("Device communication error during set_brightness: %s", exc)

    def test_connection(self) -> bool:
        """Push a solid dark blue test frame to verify device connectivity.

        Bypasses rate limiting since this is a diagnostic operation, not a
        regular frame push.

        Returns:
            True if the frame was pushed without error, False otherwise.
        """
        try:
            test_image = Image.new("RGB", (self._size, self._size), color=(0, 0, 40))
            self._pixoo.draw_image(test_image)
            self._pixoo.push()
            self._last_push_time = time.monotonic()
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device connection test failed: %s", exc)
            return False
