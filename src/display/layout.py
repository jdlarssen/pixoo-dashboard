"""Zone-based layout definitions for the 64x64 Pixoo dashboard."""

from typing import NamedTuple


class Zone(NamedTuple):
    """A rectangular region on the 64x64 display."""

    name: str
    x: int
    y: int
    width: int
    height: int


# Zone definitions -- pixel budget:
# 11 + 8 + 1 + 19 + 1 + 24 = 64px exactly
CLOCK_ZONE = Zone(name="clock", x=0, y=0, width=64, height=11)
DATE_ZONE = Zone(name="date", x=0, y=11, width=64, height=8)
DIVIDER_1 = Zone(name="divider_1", x=0, y=19, width=64, height=1)
BUS_ZONE = Zone(name="bus", x=0, y=20, width=64, height=19)
DIVIDER_2 = Zone(name="divider_2", x=0, y=39, width=64, height=1)
WEATHER_ZONE = Zone(name="weather", x=0, y=40, width=64, height=24)

# All zones by name for lookup
ZONES = {
    "clock": CLOCK_ZONE,
    "date": DATE_ZONE,
    "divider_1": DIVIDER_1,
    "bus": BUS_ZONE,
    "divider_2": DIVIDER_2,
    "weather": WEATHER_ZONE,
}

# Color constants -- cohesive LED-friendly palette
COLOR_TIME = (255, 240, 200)       # Warm white, slightly golden for LED warmth
COLOR_DATE = (120, 200, 220)       # Soft cyan tint (not grey)
COLOR_DIVIDER = (30, 60, 60)       # Subtle teal (not grey)
COLOR_PLACEHOLDER = (40, 60, 60)   # Dark teal (not grey)

# Bus zone colors
COLOR_BUS_DIR1 = (100, 200, 255)   # Light blue for Sentrum direction (arrow+letter)
COLOR_BUS_DIR2 = (255, 180, 50)    # Amber/orange for Lade direction (arrow+letter)

# Bus urgency colors (applied to countdown numbers per departure)
COLOR_URGENCY_GREEN = (50, 255, 50)      # >10 min -- plenty of time
COLOR_URGENCY_YELLOW = (255, 200, 0)     # 5-10 min -- hurry
COLOR_URGENCY_RED = (255, 50, 50)        # <5 min -- imminent
COLOR_URGENCY_DIMMED = (80, 80, 80)      # <2 min -- bus has effectively left

# Staleness indicator
COLOR_STALE_INDICATOR = (255, 100, 0)    # Orange dot for stale data

# Weather zone colors -- vivid palette
COLOR_WEATHER_TEMP = (255, 255, 255)       # White for positive temperatures
COLOR_WEATHER_TEMP_NEG = (100, 180, 255)   # Brighter blue for negative temperatures
COLOR_WEATHER_HILO = (120, 180, 160)       # Soft teal for high/low text (not grey)
COLOR_WEATHER_RAIN = (50, 180, 255)        # Vivid blue for rain indicator text

# Text positioning
TEXT_X = 2  # 2px left padding for all text


def urgency_color(minutes: int) -> tuple[int, int, int]:
    """Return RGB color for a bus departure based on urgency.

    Thresholds per user decision:
    - Green: >10 min (plenty of time)
    - Yellow: 5-10 min (hurry)
    - Red: <5 min (imminent)
    - Dimmed: <2 min (bus has effectively left)

    Args:
        minutes: Countdown minutes until departure.

    Returns:
        RGB color tuple for the departure number.
    """
    if minutes < 2:
        return COLOR_URGENCY_DIMMED
    elif minutes < 5:
        return COLOR_URGENCY_RED
    elif minutes <= 10:
        return COLOR_URGENCY_YELLOW
    else:
        return COLOR_URGENCY_GREEN
