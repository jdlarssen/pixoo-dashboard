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

# Bus departure settings (Entur JourneyPlanner v3 API)
# Quay IDs for Ladeveien (NSR:StopPlace:42686)
# Direction 1 (Sentrum): buses towards city center via Lade-sentrum-Kolstad
# Direction 2 (Lade): buses towards Strindheim via Lade
BUS_QUAY_DIRECTION1 = os.environ.get("BUS_QUAY_DIR1", "NSR:Quay:73154")
BUS_QUAY_DIRECTION2 = os.environ.get("BUS_QUAY_DIR2", "NSR:Quay:73152")
BUS_REFRESH_INTERVAL = 60  # seconds between bus API fetches
BUS_NUM_DEPARTURES = 2  # number of departures to show per direction
ET_CLIENT_NAME = os.environ.get("ET_CLIENT_NAME", "jdl-divoomhub")
ENTUR_API_URL = "https://api.entur.io/journey-planner/v3/graphql"
