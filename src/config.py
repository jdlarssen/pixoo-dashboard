"""Configuration constants for Divoom Hub."""

import os
from pathlib import Path

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Device settings
DEVICE_IP = os.environ.get("DIVOOM_IP", "192.168.1.100")
DISPLAY_SIZE = 64
PUSH_INTERVAL = 1  # seconds between state checks

# Font settings
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_LARGE = "7x13"   # for clock digits
FONT_SMALL = "5x8"    # for date and labels
FONT_TINY = "4x6"     # for zone labels

# Device safety
MAX_BRIGHTNESS = 90  # cap at 90% -- full brightness can crash device
