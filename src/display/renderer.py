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
    COLOR_WEATHER_HILO,
    COLOR_WEATHER_RAIN,
    COLOR_WEATHER_TEMP,
    COLOR_WEATHER_TEMP_NEG,
    DATE_ZONE,
    DIVIDER_1,
    DIVIDER_2,
    TEXT_X,
    WEATHER_ZONE,
)
from src.display.state import DisplayState
from src.display.weather_icons import get_weather_icon


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


def render_weather_zone(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    state: DisplayState,
    fonts: dict,
    anim_frame: Image.Image | None = None,
) -> None:
    """Render the weather zone with temperature, high/low, and rain indicator.

    Layout within the 20px weather zone (y=44 to y=63):
    - Row 1 (y+1): Current temperature (large-ish) + rain indicator
    - Row 2 (y+11): High/low temperatures in dim gray

    Animation background is composited first, then text drawn on top.

    Args:
        draw: PIL ImageDraw instance.
        img: The base RGB image (for compositing animation overlay).
        state: Current display state with weather data.
        fonts: Font dictionary with "small" (5x8) and "tiny" (4x6) keys.
        anim_frame: Optional RGBA animation overlay (64x20).
    """
    zone_y = WEATHER_ZONE.y

    # Composite animation background if available
    if anim_frame is not None:
        # Single-pass alpha composite: extract the zone region, composite once, paste back.
        # Previous code applied alpha twice (alpha_composite + paste mask), squashing
        # effective opacity from ~20% to ~4% -- invisible on LED hardware.
        zone_region = img.crop((0, zone_y, anim_frame.width, zone_y + anim_frame.height)).convert("RGBA")
        composited = Image.alpha_composite(zone_region, anim_frame)
        img.paste(composited.convert("RGB"), (0, zone_y))

    if state.weather_temp is None:
        # No weather data -- show placeholder
        draw.text(
            (TEXT_X, zone_y + 1),
            "---",
            font=fonts["small"],
            fill=COLOR_PLACEHOLDER,
        )
        return

    # Current temperature -- use small font for readability
    temp_value = state.weather_temp
    if temp_value < 0:
        temp_color = COLOR_WEATHER_TEMP_NEG
        temp_text = str(abs(temp_value))
    else:
        temp_color = COLOR_WEATHER_TEMP
        temp_text = str(temp_value)

    draw.text(
        (TEXT_X, zone_y + 1),
        temp_text,
        font=fonts["small"],
        fill=temp_color,
    )

    # Calculate width of temperature text for positioning high/low
    temp_bbox = fonts["small"].getbbox(temp_text)
    temp_width = temp_bbox[2] - temp_bbox[0] if temp_bbox else len(temp_text) * 6

    # High/low on same row, right of current temp -- tiny font, dim gray
    if state.weather_high is not None and state.weather_low is not None:
        hilo_text = f"{state.weather_high}/{state.weather_low}"
        hilo_x = TEXT_X + temp_width + 5  # 5px gap
        draw.text(
            (hilo_x, zone_y + 2),  # slight y offset to align with small font baseline
            hilo_text,
            font=fonts["tiny"],
            fill=COLOR_WEATHER_HILO,
        )

    # Rain indicator -- show precipitation amount if > 0
    if state.weather_precip_mm is not None and state.weather_precip_mm > 0:
        rain_text = f"{state.weather_precip_mm:.1f}mm"
        draw.text(
            (TEXT_X, zone_y + 11),
            rain_text,
            font=fonts["tiny"],
            fill=COLOR_WEATHER_RAIN,
        )


def render_frame(
    state: DisplayState,
    fonts: dict,
    anim_frame: Image.Image | None = None,
) -> Image.Image:
    """Render the dashboard state into a 64x64 RGB PIL Image.

    This function only renders from the provided state -- it does NOT
    fetch any data. Keep rendering and data collection separate.

    Args:
        state: Current display data (time string, date string).
        fonts: Dictionary with keys "large", "small", "tiny" mapping
               to PIL ImageFont objects.
        anim_frame: Optional RGBA animation overlay for weather zone (64x20).

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

    # Weather icon next to clock (right of time digits)
    if state.weather_symbol is not None:
        time_bbox = fonts["large"].getbbox(state.time_str)
        time_width = time_bbox[2] - time_bbox[0] if time_bbox else len(state.time_str) * 8
        icon = get_weather_icon(state.weather_symbol, size=10)
        icon_x = TEXT_X + time_width + 2  # 2px gap after time text
        icon_y = CLOCK_ZONE.y + 2  # slight vertical offset to center in clock zone
        # Only paste if icon fits within display width
        if icon_x + icon.width <= 64:
            img.paste(icon.convert("RGB"), (icon_x, icon_y), mask=icon.split()[3])

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

    # Weather zone -- temperature, high/low, rain indicator with animated background
    render_weather_zone(draw, img, state, fonts, anim_frame)

    return img
