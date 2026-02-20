"""PIL compositor that renders DisplayState into a 64x64 dashboard image."""

from PIL import Image, ImageDraw

from src.config import BUS_NUM_DEPARTURES
from src.display.layout import (
    BUS_ZONE,
    CLOCK_ZONE,
    COLOR_BUS_DIR1,
    COLOR_BUS_DIR2,
    COLOR_DATE,
    COLOR_DIVIDER,
    COLOR_MESSAGE,
    COLOR_PLACEHOLDER,
    COLOR_STALE_INDICATOR,
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
    urgency_color,
)
from src.display.state import DisplayState
from src.display.weather_icons import get_weather_icon


def render_bus_zone(
    draw: ImageDraw.ImageDraw,
    state: DisplayState,
    fonts: dict,
) -> None:
    """Render the bus departure zone with two direction lines.

    Layout within the 19px bus zone (y=20 to y=38):
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
    """Draw a single bus direction line with colored label and urgency-colored times.

    Each departure countdown number is drawn individually with its own urgency
    color based on the minute value (green >10, yellow 5-10, red <5, dimmed <2).
    Direction labels retain their original colors per user decision.

    Args:
        draw: PIL ImageDraw instance.
        x: Starting x coordinate.
        y: Starting y coordinate.
        label: Direction label (e.g. ">S").
        departures: Countdown minutes tuple or None.
        label_color: RGB color for the direction label.
        font: PIL font to use.
    """
    # Draw label in direction color (unchanged -- user decision)
    draw.text((x, y), label, font=font, fill=label_color)

    # Calculate label width to position countdown numbers after it
    label_bbox = font.getbbox(label)
    label_width = label_bbox[2] - label_bbox[0] if label_bbox else len(label) * 6

    # Starting x position for countdown numbers
    cursor_x = x + label_width + 4  # 4px gap between label and times

    # Measure space character width for consistent spacing
    space_bbox = font.getbbox(" ")
    space_width = space_bbox[2] - space_bbox[0] if space_bbox else 3

    # Draw each departure number individually with its own urgency color
    for i in range(BUS_NUM_DEPARTURES):
        if i > 0:
            cursor_x += space_width  # space between numbers

        if departures is not None and i < len(departures):
            text = str(departures[i])
            color = urgency_color(departures[i])
        else:
            text = "--"
            color = COLOR_PLACEHOLDER

        draw.text((cursor_x, y), text, font=font, fill=color)

        # Advance cursor by text width
        text_bbox = font.getbbox(text)
        text_width = text_bbox[2] - text_bbox[0] if text_bbox else len(text) * 6
        cursor_x += text_width


def render_weather_zone(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    state: DisplayState,
    fonts: dict,
    anim_frame: Image.Image | None = None,
) -> None:
    """Render the weather zone with temperature, high/low, and rain indicator.

    Layout within the 24px weather zone (y=40 to y=63):
    - Row 1 (y+1): Current temperature + rain indicator
    - Row 2 (y+11): High/low temperatures in soft teal

    Animation background is composited first, then text drawn on top.

    Args:
        draw: PIL ImageDraw instance.
        img: The base RGB image (for compositing animation overlay).
        state: Current display state with weather data.
        fonts: Font dictionary with "small" (5x8) and "tiny" (4x6) keys.
        anim_frame: Optional RGBA animation overlay (64x24).
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
    # When message is active, skip rain to make room for message text
    if state.message_text is None:
        if state.weather_precip_mm is not None and state.weather_precip_mm > 0:
            rain_text = f"{state.weather_precip_mm:.1f}mm"
            draw.text(
                (TEXT_X, zone_y + 11),
                rain_text,
                font=fonts["tiny"],
                fill=COLOR_WEATHER_RAIN,
            )

    # Message overlay -- persistent Discord message in bottom of weather zone
    if state.message_text is not None:
        _render_message(draw, zone_y, state.message_text, fonts)


def _render_message(
    draw: ImageDraw.ImageDraw,
    zone_y: int,
    text: str,
    fonts: dict,
) -> None:
    """Render a persistent message in the bottom portion of the weather zone.

    Uses the tiny (4x6) font. Truncates to fit within 64px display width.
    Renders up to 2 lines starting at zone_y + 12 (below weather data).

    Args:
        draw: PIL ImageDraw instance.
        zone_y: Top y coordinate of the weather zone.
        text: Message text to display.
        fonts: Font dictionary with "tiny" (4x6) key.
    """
    font = fonts["tiny"]
    max_width = 64 - TEXT_X - 1  # 1px right margin

    # Split into lines that fit within max_width
    lines = _wrap_text(text, font, max_width)

    # Render up to 2 lines in the bottom portion of the weather zone
    line_height = 7  # 6px font + 1px gap
    start_y = zone_y + 12  # Below temperature/hilo row
    for i, line in enumerate(lines[:2]):
        draw.text(
            (TEXT_X, start_y + i * line_height),
            line,
            font=font,
            fill=COLOR_MESSAGE,
        )


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap text into lines that fit within max_width pixels.

    Args:
        text: Text to wrap.
        font: PIL font for measuring text width.
        max_width: Maximum line width in pixels.

    Returns:
        List of text lines, each fitting within max_width.
    """
    words = text.split()
    if not words:
        return []

    lines = []
    current_line = words[0]

    for word in words[1:]:
        test_line = current_line + " " + word
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0] if bbox else len(test_line) * 5
        if line_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)

    # Truncate last visible line with "..." if there are more lines
    if len(lines) > 2:
        last_line = lines[1]
        # Try to fit with ellipsis
        while last_line:
            test = last_line + "..."
            bbox = font.getbbox(test)
            width = bbox[2] - bbox[0] if bbox else len(test) * 5
            if width <= max_width:
                lines[1] = test
                break
            last_line = last_line[:-1]

    return lines


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
        anim_frame: Optional RGBA animation overlay for weather zone (64x24).

    Returns:
        A 64x64 RGB PIL Image ready for pushing to the device.
    """
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Clock time -- small font for compact 11px zone (still readable on LED)
    draw.text(
        (TEXT_X, CLOCK_ZONE.y + 1),
        state.time_str,
        font=fonts["small"],
        fill=COLOR_TIME,
    )

    # Weather icon next to clock (right of time digits)
    if state.weather_symbol is not None:
        time_bbox = fonts["small"].getbbox(state.time_str)
        time_width = time_bbox[2] - time_bbox[0] if time_bbox else len(state.time_str) * 6
        icon = get_weather_icon(state.weather_symbol, size=10)
        icon_x = TEXT_X + time_width + 2  # 2px gap after time text
        icon_y = CLOCK_ZONE.y + 1  # align with text in compact 11px clock zone
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

    # Staleness indicator for bus data (orange dot at top-right of bus zone)
    if state.bus_stale and not state.bus_too_old:
        draw.point((62, BUS_ZONE.y + 1), fill=COLOR_STALE_INDICATOR)

    # Divider line 2 (between bus and weather zone)
    draw.line(
        [(0, DIVIDER_2.y), (63, DIVIDER_2.y)],
        fill=COLOR_DIVIDER,
    )

    # Weather zone -- temperature, high/low, rain indicator with animated background
    render_weather_zone(draw, img, state, fonts, anim_frame)

    # Staleness indicator for weather data (orange dot at top-right of weather zone)
    if state.weather_stale and not state.weather_too_old:
        draw.point((62, WEATHER_ZONE.y + 1), fill=COLOR_STALE_INDICATOR)

    return img
