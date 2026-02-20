"""Pixoo 64 device communication wrapper with connection refresh and rate limiting."""

import logging
import time

from PIL import Image

from src.config import DISPLAY_SIZE, MAX_BRIGHTNESS

logger = logging.getLogger(__name__)


class PixooClient:
    """Wrapper around the pixoo library's Pixoo class.

    Provides:
    - Connection refresh to prevent the ~300-push lockup (enabled by default in pixoo lib)
    - Rate-limited frame pushing (minimum 0.3s between pushes, ~3 FPS max)
    - Brightness control capped at MAX_BRIGHTNESS (90%)
    - Simulator mode for development without hardware
    """

    def __init__(self, ip: str, size: int = DISPLAY_SIZE, simulated: bool = False):
        """Initialize the Pixoo device connection.

        Args:
            ip: Device IP address on the local network.
            size: Display size in pixels (64 for Pixoo 64).
            simulated: If True, use the pixoo library's Tkinter simulator.
        """
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

    def push_frame(self, image: Image.Image) -> None:
        """Push a PIL Image frame to the device.

        Enforces a minimum 0.3-second (300ms) interval between pushes. The
        Pixoo 64 handles ~3 FPS over HTTP reliably. If called too soon after
        the last push, the call is skipped with a warning.

        Args:
            image: A PIL RGB Image (should be 64x64 for Pixoo 64).
        """
        now = time.monotonic()
        elapsed = now - self._last_push_time

        if self._last_push_time > 0 and elapsed < 0.3:
            logger.warning(
                "Push skipped: only %.2fs since last push (minimum 0.3s interval)", elapsed
            )
            return

        self._pixoo.draw_image(image)
        self._pixoo.push()
        self._last_push_time = time.monotonic()

    def set_brightness(self, level: int) -> None:
        """Set device brightness, capped at MAX_BRIGHTNESS.

        Args:
            level: Brightness level (0-100). Will be capped at MAX_BRIGHTNESS (90).
        """
        capped = min(level, MAX_BRIGHTNESS)
        if level > MAX_BRIGHTNESS:
            logger.info(
                "Brightness %d exceeds max (%d), capping at %d", level, MAX_BRIGHTNESS, capped
            )
        self._pixoo.set_brightness(capped)

    def test_connection(self) -> bool:
        """Push a solid dark blue test frame to verify device connectivity.

        Returns:
            True if the frame was pushed without error, False otherwise.
        """
        try:
            test_image = Image.new("RGB", (self._size, self._size), color=(0, 0, 40))
            self.push_frame(test_image)
            return True
        except Exception:
            logger.exception("Device connection test failed")
            return False
