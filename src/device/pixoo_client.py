"""Pixoo 64 device communication wrapper with connection refresh and rate limiting.

The Pixoo 64 device has a documented limitation: its embedded HTTP server
cannot reliably handle more than ~1 request per second. Exceeding this rate
causes the device to drop connections and eventually freeze.

This wrapper enforces safe timing, adds timeouts to all device HTTP calls
(the upstream pixoo library uses none), and implements error cooldown to
prevent cascading failures when the device is in a degraded state.
"""

import functools
import logging
import threading
import time

import requests as _requests_module
from PIL import Image
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

# Backward-compatible aliases for tests and internal use
_DEVICE_TIMEOUT = DEVICE_HTTP_TIMEOUT
_MIN_PUSH_INTERVAL = DEVICE_MIN_PUSH_INTERVAL
_ERROR_COOLDOWN_BASE = DEVICE_ERROR_COOLDOWN_BASE
_ERROR_COOLDOWN_MAX = DEVICE_ERROR_COOLDOWN_MAX
_patch_lock = threading.Lock()


def _is_local_device_url(url: str) -> bool:
    """Check if a URL targets an RFC 1918 private IP address.

    Matches 10.x.x.x, 172.16-31.x.x, and 192.168.x.x ranges.
    """
    if not isinstance(url, str) or not url.startswith("http://"):
        return False
    # Extract host portion: "http://10.0.0.1/post" -> "10.0.0.1"
    host = url[7:].split("/", 1)[0].split(":")[0]
    if host.startswith("10."):
        return True
    if host.startswith("192.168."):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
            except ValueError:
                pass
    return False


def _patch_requests_post(original_post):
    """Wrap requests.post to inject a default timeout when calling the device.

    The pixoo library calls ``requests.post(url, payload)`` with no timeout,
    meaning a hung device blocks the caller indefinitely. This wrapper adds
    a timeout to any POST that targets an RFC 1918 private IP address.
    Non-device calls (e.g., to external APIs) are left untouched.
    """
    @functools.wraps(original_post)
    def _post_with_timeout(*args, **kwargs):
        url = args[0] if args else kwargs.get("url", "")
        # Only inject timeout for device calls (local HTTP), not external APIs
        if "timeout" not in kwargs and _is_local_device_url(url):
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
        # Patch requests.post on the pixoo module only (not globally) so that
        # device HTTP calls from the pixoo library get a timeout.
        import pixoo.objects.pixoo as _pixoo_module
        with _patch_lock:
            if not getattr(
                getattr(_pixoo_module, "requests", _requests_module).post,
                "_patched_with_timeout",
                False,
            ):
                _target = getattr(_pixoo_module, "requests", _requests_module)
                _target.post = _patch_requests_post(_target.post)
                _target.post._patched_with_timeout = True  # type: ignore[attr-defined]

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
            self._error_until = time.monotonic() + self._current_cooldown
            logger.info("Device cooldown: pausing pushes for %.0fs (backoff)", self._current_cooldown)
            self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
            return False
        self._current_cooldown = _ERROR_COOLDOWN_BASE
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
            self._current_cooldown = _ERROR_COOLDOWN_BASE
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device ping failed: %s", exc)
            self._error_until = time.monotonic() + self._current_cooldown
            self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
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
