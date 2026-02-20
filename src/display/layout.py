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

# Text positioning
TEXT_X = 2  # 2px left padding for all text
