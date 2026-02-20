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
# 14 + 9 + 1 + 19 + 1 + 20 = 64px exactly
CLOCK_ZONE = Zone(name="clock", x=0, y=0, width=64, height=14)
DATE_ZONE = Zone(name="date", x=0, y=14, width=64, height=9)
DIVIDER_1 = Zone(name="divider_1", x=0, y=23, width=64, height=1)
BUS_ZONE = Zone(name="bus", x=0, y=24, width=64, height=19)
DIVIDER_2 = Zone(name="divider_2", x=0, y=43, width=64, height=1)
WEATHER_ZONE = Zone(name="weather", x=0, y=44, width=64, height=20)

# All zones by name for lookup
ZONES = {
    "clock": CLOCK_ZONE,
    "date": DATE_ZONE,
    "divider_1": DIVIDER_1,
    "bus": BUS_ZONE,
    "divider_2": DIVIDER_2,
    "weather": WEATHER_ZONE,
}

# Color constants
COLOR_TIME = (255, 255, 255)       # Bright white for clock
COLOR_DATE = (180, 180, 180)       # Dim white for date
COLOR_DIVIDER = (40, 40, 40)       # Subtle gray divider
COLOR_PLACEHOLDER = (60, 60, 60)   # Very dim for placeholder text

# Bus zone colors
COLOR_BUS_DIR1 = (100, 200, 255)   # Light blue for Sentrum direction (arrow+letter)
COLOR_BUS_DIR2 = (255, 180, 50)    # Amber/orange for Lade direction (arrow+letter)
COLOR_BUS_TIME = (255, 255, 255)   # White for departure countdown numbers

# Bus urgency colors (applied to countdown numbers per departure)
COLOR_URGENCY_GREEN = (50, 255, 50)      # >10 min -- plenty of time
COLOR_URGENCY_YELLOW = (255, 200, 0)     # 5-10 min -- hurry
COLOR_URGENCY_RED = (255, 50, 50)        # <5 min -- imminent
COLOR_URGENCY_DIMMED = (80, 80, 80)      # <2 min -- bus has effectively left

# Staleness indicator
COLOR_STALE_INDICATOR = (255, 100, 0)    # Orange dot for stale data

# Weather zone colors
COLOR_WEATHER_TEMP = (255, 255, 255)       # White for positive temperatures
COLOR_WEATHER_TEMP_NEG = (100, 160, 255)   # Blue for negative temperatures (no minus sign)
COLOR_WEATHER_HILO = (140, 140, 140)       # Dim gray for high/low text
COLOR_WEATHER_RAIN = (80, 160, 255)        # Blue tint for rain indicator text

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
