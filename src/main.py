"""Divoom Hub dashboard entry point.

Renders a clock dashboard on the Pixoo 64 with Norwegian date formatting.
Updates the display only when the minute changes (dirty flag pattern).

Usage:
    python src/main.py --ip 192.168.1.100
    python src/main.py --simulated --save-frame
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work when run directly
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import (
    BUS_REFRESH_INTERVAL,
    DEVICE_IP,
    FONT_DIR,
    FONT_LARGE,
    FONT_SMALL,
    FONT_TINY,
    MAX_BRIGHTNESS,
)
from src.providers.bus import fetch_bus_data
from src.device.pixoo_client import PixooClient
from src.display.fonts import load_fonts
from src.display.renderer import render_frame
from src.display.state import DisplayState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_font_map(font_dir: str) -> dict:
    """Load fonts and map them to logical names used by the renderer.

    Args:
        font_dir: Directory containing BDF font files.

    Returns:
        Dictionary with keys "large", "small", "tiny" mapping to PIL fonts.
    """
    raw_fonts = load_fonts(font_dir)
    return {
        "large": raw_fonts[FONT_LARGE],
        "small": raw_fonts[FONT_SMALL],
        "tiny": raw_fonts[FONT_TINY],
    }


def main_loop(
    client: PixooClient,
    fonts: dict,
    *,
    save_frame: bool = False,
) -> None:
    """Run the dashboard main loop.

    Checks time every second. Only re-renders and pushes a frame when the
    display state changes (i.e., when the minute changes).

    Args:
        client: Pixoo device client for pushing frames.
        fonts: Font dictionary with keys "large", "small", "tiny".
        save_frame: If True, save each rendered frame to debug_frame.png.
    """
    last_state = None
    last_bus_fetch = 0.0  # monotonic() is always > 60 on a running system
    bus_data: tuple[list[int] | None, list[int] | None] = (None, None)

    while True:
        # Independent 60-second bus data refresh
        now_mono = time.monotonic()
        if now_mono - last_bus_fetch >= BUS_REFRESH_INTERVAL:
            bus_data = fetch_bus_data()
            last_bus_fetch = now_mono
            logger.info("Bus data refreshed: dir1=%s dir2=%s", bus_data[0], bus_data[1])

        now = datetime.now()
        current_state = DisplayState.from_now(now, bus_data=bus_data)

        if current_state != last_state:
            frame = render_frame(current_state, fonts)

            if save_frame:
                frame.save("debug_frame.png")
                logger.info("Saved debug_frame.png")

            client.push_frame(frame)
            logger.info("Pushed frame: %s %s", current_state.time_str, current_state.date_str)
            last_state = current_state

        time.sleep(1)


def main() -> None:
    """Parse arguments and start the dashboard."""
    parser = argparse.ArgumentParser(description="Divoom Hub - Pixoo 64 Dashboard")
    parser.add_argument(
        "--ip",
        default=DEVICE_IP,
        help=f"Pixoo 64 device IP address (default: {DEVICE_IP})",
    )
    parser.add_argument(
        "--simulated",
        action="store_true",
        default=False,
        help="Run in simulator mode (Tkinter window, no hardware needed)",
    )
    parser.add_argument(
        "--save-frame",
        action="store_true",
        default=False,
        help="Save each rendered frame to debug_frame.png",
    )
    args = parser.parse_args()

    logger.info("Loading fonts from %s", FONT_DIR)
    fonts = build_font_map(FONT_DIR)
    logger.info("Fonts loaded: %s", list(fonts.keys()))

    logger.info("Connecting to Pixoo 64 at %s (simulated=%s)", args.ip, args.simulated)
    client = PixooClient(ip=args.ip, simulated=args.simulated)
    client.set_brightness(MAX_BRIGHTNESS)
    logger.info("Brightness set to %d%%", MAX_BRIGHTNESS)

    logger.info("Starting dashboard main loop (Ctrl+C to stop)")
    try:
        main_loop(client, fonts, save_frame=args.save_frame)
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
