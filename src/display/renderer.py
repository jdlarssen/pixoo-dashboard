"""PIL compositor that renders DisplayState into a 64x64 dashboard image."""

from PIL import Image, ImageDraw

from src.display.layout import (
    BUS_ZONE,
    CLOCK_ZONE,
    COLOR_DATE,
    COLOR_DIVIDER,
    COLOR_PLACEHOLDER,
    COLOR_TIME,
    DATE_ZONE,
    DIVIDER_1,
    DIVIDER_2,
    TEXT_X,
    WEATHER_ZONE,
)
from src.display.state import DisplayState


def render_frame(state: DisplayState, fonts: dict) -> Image.Image:
    """Render the dashboard state into a 64x64 RGB PIL Image.

    This function only renders from the provided state -- it does NOT
    fetch any data. Keep rendering and data collection separate.

    Args:
        state: Current display data (time string, date string).
        fonts: Dictionary with keys "large", "small", "tiny" mapping
               to PIL ImageFont objects.

    Returns:
        A 64x64 RGB PIL Image ready for pushing to the device.
    """
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Clock time -- large white digits
    draw.text(
        (TEXT_X, CLOCK_ZONE.y),
        state.time_str,
        font=fonts["large"],
        fill=COLOR_TIME,
    )

    # Date -- smaller dim white text
    draw.text(
        (TEXT_X, DATE_ZONE.y),
        state.date_str,
        font=fonts["small"],
        fill=COLOR_DATE,
    )

    # Divider line 1 (between date and bus zone)
    draw.line(
        [(0, DIVIDER_1.y), (63, DIVIDER_1.y)],
        fill=COLOR_DIVIDER,
    )

    # Bus zone placeholder
    draw.text(
        (TEXT_X, BUS_ZONE.y + 1),
        "BUS",
        font=fonts["tiny"],
        fill=COLOR_PLACEHOLDER,
    )

    # Divider line 2 (between bus and weather zone)
    draw.line(
        [(0, DIVIDER_2.y), (63, DIVIDER_2.y)],
        fill=COLOR_DIVIDER,
    )

    # Weather zone placeholder -- "V\u00c6R" (Norwegian for weather)
    draw.text(
        (TEXT_X, WEATHER_ZONE.y + 1),
        "V\u00c6R",
        font=fonts["tiny"],
        fill=COLOR_PLACEHOLDER,
    )

    return img
