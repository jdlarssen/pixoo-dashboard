"""Pixoo 64 device communication wrapper with connection refresh and rate limiting.

The Pixoo 64 device has a documented limitation: its embedded HTTP server
cannot reliably handle more than ~1 request per second. Exceeding this rate
causes the device to drop connections and eventually freeze.

This wrapper enforces safe timing, adds timeouts to all device HTTP calls
(the upstream pixoo library uses none), and implements error cooldown to
prevent cascading failures when the device is in a degraded state.
"""

import functools
import json
import logging
import time

import requests as _requests_module
from PIL import Image
from requests.exceptions import RequestException

from src.config import DISPLAY_SIZE, MAX_BRIGHTNESS

logger = logging.getLogger(__name__)

# Device HTTP timeout -- the pixoo library's requests.post() calls have no
# timeout, so a hung device blocks the main loop indefinitely.  We monkey-patch
# the module-level requests.post used by the pixoo library to inject one.
_DEVICE_TIMEOUT = 5  # seconds

# Minimum interval between frame pushes (seconds).  The Pixoo 64 documentation
# says "do not call push() more than once per second".  We enforce 1.0s.
_MIN_PUSH_INTERVAL = 1.0

# After a device communication error, pause before retrying to let the
# device's embedded HTTP server recover.
_ERROR_COOLDOWN = 3.0  # seconds


def _patch_requests_post(original_post):
    """Wrap requests.post to inject a default timeout when calling the device.

    The pixoo library calls ``requests.post(url, payload)`` with no timeout,
    meaning a hung device blocks the caller indefinitely. This wrapper adds
    a timeout to any POST that targets a local device IP (``http://192.*``).
    Non-device calls (e.g., to external APIs) are left untouched.
    """
    @functools.wraps(original_post)
    def _post_with_timeout(*args, **kwargs):
        url = args[0] if args else kwargs.get("url", "")
        # Only inject timeout for device calls (local HTTP), not external APIs
        if "timeout" not in kwargs and isinstance(url, str) and url.startswith("http://192."):
            kwargs["timeout"] = _DEVICE_TIMEOUT
        return original_post(*args, **kwargs)
    return _post_with_timeout


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
        # Monkey-patch requests.post BEFORE importing pixoo so that all
        # device HTTP calls from the pixoo library get a timeout.
        import pixoo.objects.pixoo as _pixoo_module
        if not getattr(_requests_module.post, "_patched_with_timeout", False):
            _requests_module.post = _patch_requests_post(_requests_module.post)
            _requests_module.post._patched_with_timeout = True  # type: ignore[attr-defined]

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

    def push_frame(self, image: Image.Image) -> bool | None:
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
            True if the frame was delivered to the device.
            False if a communication error occurred (device unreachable).
            None if the push was skipped (rate limit or error cooldown).
        """
        now = time.monotonic()

        # Respect error cooldown
        if now < self._error_until:
            return None

        # Rate limit: enforce minimum interval
        elapsed = now - self._last_push_time
        if self._last_push_time > 0 and elapsed < _MIN_PUSH_INTERVAL:
            return None

        try:
            self._pixoo.draw_image(image)
            self._pixoo.push()
        except (RequestException, OSError) as exc:
            logger.warning("Device communication error during push_frame: %s", exc)
            self._error_until = time.monotonic() + _ERROR_COOLDOWN
            logger.info("Device cooldown: pausing pushes for %.0fs", _ERROR_COOLDOWN)
            return False
        self._last_push_time = time.monotonic()
        return True

    def ping(self) -> bool | None:
        """Send a lightweight health-check to keep the device WiFi alive.

        Uses Channel/GetAllConf which returns device config without any
        visual side-effect. Respects error cooldown.

        Returns:
            True if device responded, False on communication error,
            None if skipped (error cooldown active).
        """
        now = time.monotonic()
        if now < self._error_until:
            return None

        try:
            self._pixoo.validate_connection()
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device ping failed: %s", exc)
            self._error_until = time.monotonic() + _ERROR_COOLDOWN
            return False

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
                json.dumps({"Command": "Device/SysReboot"}),
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

        Returns:
            True if the frame was pushed without error, False otherwise.
        """
        try:
            test_image = Image.new("RGB", (self._size, self._size), color=(0, 0, 40))
            result = self.push_frame(test_image)
            return result is True
        except Exception:
            logger.exception("Device connection test failed")
            return False
