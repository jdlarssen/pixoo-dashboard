"""PIL compositor that renders DisplayState into a 64x64 dashboard image."""

from PIL import Image, ImageDraw

from src.config import BUS_NUM_DEPARTURES
from src.display.layout import (
    BUS_ZONE,
    CLOCK_ZONE,
    COLOR_BUS_DIR1,
    COLOR_BUS_DIR2,
    COLOR_BUS_TIME,
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


def render_bus_zone(
    draw: ImageDraw.ImageDraw,
    state: DisplayState,
    fonts: dict,
) -> None:
    """Render the bus departure zone with two direction lines.

    Layout within the 19px bus zone (y=24 to y=42):
    - Line 1 (direction 1 / Sentrum): y = BUS_ZONE.y + 1 (1px top padding)
    - Line 2 (direction 2 / Lade): y = BUS_ZONE.y + 10 (1px gap after 8px line)
    - Total: 1px + 8px + 1px + 8px + 1px = 19px

    Each line: arrow+letter label in direction color, countdown numbers in white.

    Args:
        draw: PIL ImageDraw instance.
        state: Current display state with bus departure data.
        fonts: Font dictionary with "small" (5x8) and "tiny" (4x6) keys.
    """
    font = fonts["small"]  # 5x8 for better readability of countdown numbers

    # Direction 1 (Sentrum) -- top line, arrow points left (towards city center)
    _draw_bus_line(draw, TEXT_X, BUS_ZONE.y + 1, "<S", state.bus_direction1, COLOR_BUS_DIR1, font)

    # Direction 2 (Lade) -- bottom line, arrow points right (towards Lade/Strindheim)
    _draw_bus_line(draw, TEXT_X, BUS_ZONE.y + 10, ">L", state.bus_direction2, COLOR_BUS_DIR2, font)


def _draw_bus_line(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    departures: tuple[int, ...] | None,
    label_color: tuple[int, int, int],
    font,
) -> None:
    """Draw a single bus direction line with colored label and white times.

    Args:
        draw: PIL ImageDraw instance.
        x: Starting x coordinate.
        y: Starting y coordinate.
        label: Direction label (e.g. ">S").
        departures: Countdown minutes tuple or None.
        label_color: RGB color for the direction label.
        font: PIL font to use.
    """
    # Draw label in direction color
    draw.text((x, y), label, font=font, fill=label_color)

    # Calculate label width to position countdown numbers after it
    label_bbox = font.getbbox(label)
    label_width = label_bbox[2] - label_bbox[0] if label_bbox else len(label) * 6

    # Format countdown numbers
    if departures is None:
        time_str = " ".join(["--"] * BUS_NUM_DEPARTURES)
    else:
        parts = []
        for i in range(BUS_NUM_DEPARTURES):
            if i < len(departures):
                parts.append(str(departures[i]))
            else:
                parts.append("--")
        time_str = " ".join(parts)

    # Draw countdown numbers in white, with spacing after label
    time_x = x + label_width + 4  # 4px gap between label and times
    time_color = COLOR_BUS_TIME if departures is not None else COLOR_PLACEHOLDER
    draw.text((time_x, y), time_str, font=font, fill=time_color)


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

    # Bus zone -- two direction lines with colored labels and countdown numbers
    render_bus_zone(draw, state, fonts)

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
