"""PIL compositor that renders DisplayState into a 64x64 dashboard image."""

import hashlib

from PIL import Image, ImageDraw

from src.config import BUS_NUM_DEPARTURES
from src.display.layout import (
    BUS_ZONE,
    CLOCK_ZONE,
    COLOR_BIRTHDAY_ACCENT,
    COLOR_BIRTHDAY_CROWN,
    COLOR_BIRTHDAY_GOLD,
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
    MESSAGE_X,
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


def _composite_layer(img: Image.Image, layer: Image.Image, zone_y: int) -> None:
    """Alpha-composite an RGBA layer onto the image at the weather zone position."""
    zone_region = img.crop((0, zone_y, layer.width, zone_y + layer.height)).convert("RGBA")
    composited = Image.alpha_composite(zone_region, layer)
    img.paste(composited.convert("RGB"), (0, zone_y))


def render_weather_zone(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    state: DisplayState,
    fonts: dict,
    anim_layers: tuple[Image.Image, Image.Image] | None = None,
) -> None:
    """Render the weather zone with 3D layered animation.

    Compositing order for depth effect:
    1. Background animation layer (behind text -- far/dim particles)
    2. Weather text (temperature, high/low, rain)
    3. Foreground animation layer (in front of text -- near/bright particles)

    Args:
        draw: PIL ImageDraw instance.
        img: The base RGB image (for compositing animation overlays).
        state: Current display state with weather data.
        fonts: Font dictionary with "small" (5x8) and "tiny" (4x6) keys.
        anim_layers: Optional (bg_layer, fg_layer) RGBA overlays (64x24 each).
    """
    zone_y = WEATHER_ZONE.y

    # 1. Composite background layer (behind text)
    if anim_layers is not None:
        _composite_layer(img, anim_layers[0], zone_y)

    if state.weather_temp is None:
        # No weather data -- show placeholder
        draw.text(
            (TEXT_X, zone_y + 1),
            "---",
            font=fonts["small"],
            fill=COLOR_PLACEHOLDER,
        )
        return

    # 2. Draw weather text on top of background layer
    temp_value = state.weather_temp
    if temp_value < 0:
        temp_color = COLOR_WEATHER_TEMP_NEG
        temp_text = f"-{abs(temp_value)}"
    else:
        temp_color = COLOR_WEATHER_TEMP
        temp_text = str(temp_value)

    draw.text(
        (TEXT_X, zone_y + 1),
        temp_text,
        font=fonts["small"],
        fill=temp_color,
    )

    # High/low below current temp -- tiny font, soft teal (always visible)
    if state.weather_high is not None and state.weather_low is not None:
        hilo_text = f"{state.weather_high}/{state.weather_low}"
        draw.text(
            (TEXT_X, zone_y + 10),
            hilo_text,
            font=fonts["tiny"],
            fill=COLOR_WEATHER_HILO,
        )

    # Rain indicator -- below high/low line (always visible)
    if state.weather_precip_mm is not None and state.weather_precip_mm > 0:
        rain_text = f"{state.weather_precip_mm:.1f}mm"
        draw.text(
            (TEXT_X, zone_y + 17),
            rain_text,
            font=fonts["tiny"],
            fill=COLOR_WEATHER_RAIN,
        )

    # Message overlay
    if state.message_text is not None:
        _render_message(draw, zone_y, state.message_text, fonts)

    # 3. Composite foreground layer (in front of text)
    if anim_layers is not None:
        _composite_layer(img, anim_layers[1], zone_y)


def _render_message(
    draw: ImageDraw.ImageDraw,
    zone_y: int,
    text: str,
    fonts: dict,
) -> None:
    """Render a persistent Discord message on the right side of the weather zone.

    Uses the tiny (4x6) font. Positioned at MESSAGE_X (x=22), rendering up to
    3 lines starting at zone_y + 1 (aligned with the current temperature).
    Coexists with temp/hilo/precip on the left side.

    Args:
        draw: PIL ImageDraw instance.
        zone_y: Top y coordinate of the weather zone.
        text: Message text to display.
        fonts: Font dictionary with "tiny" (4x6) key.
    """
    font = fonts["tiny"]
    max_width = 64 - MESSAGE_X - 1  # 1px right margin from MESSAGE_X start

    # Split into lines that fit within max_width
    lines = _wrap_text(text, font, max_width)

    # Render up to 3 lines on the right side of the weather zone
    # Starts at zone_y + 1 (aligned with current temp row)
    line_height = 7  # 6px font + 1px gap
    start_y = zone_y + 1  # First line of zone (aligned with temp)
    for i, line in enumerate(lines[:3]):
        draw.text(
            (MESSAGE_X, start_y + i * line_height),
            line,
            font=font,
            fill=COLOR_MESSAGE,
        )


def _sanitize_for_font(text: str) -> str:
    """Remove characters outside Latin-1 range that BDF fonts cannot render.

    This is a defensive fallback -- primary sanitization happens in
    MessageBridge.set_message(). This prevents UnicodeEncodeError if
    non-Latin-1 text reaches the renderer through any code path.

    Args:
        text: Text that may contain non-Latin-1 characters.

    Returns:
        Text with only Latin-1 characters (code points 0-255).
    """
    return "".join(ch for ch in text if ord(ch) <= 255)


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap text into lines that fit within max_width pixels.

    Args:
        text: Text to wrap.
        font: PIL font for measuring text width.
        max_width: Maximum line width in pixels.

    Returns:
        List of text lines, each fitting within max_width.
    """
    text = _sanitize_for_font(text)
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

    # Truncate last visible line with "..." if there are more lines than fit
    max_lines = 3
    if len(lines) > max_lines:
        last_line = lines[max_lines - 1]
        # Try to fit with ellipsis
        while last_line:
            test = last_line + "..."
            bbox = font.getbbox(test)
            width = bbox[2] - bbox[0] if bbox else len(test) * 5
            if width <= max_width:
                lines[max_lines - 1] = test
                break
            last_line = last_line[:-1]

    return lines


def _draw_birthday_crown(draw: ImageDraw.ImageDraw) -> None:
    """Draw a small 5x5 pixel crown icon at top-right of clock zone.

    Crown pattern (5x5, starting at x=58, y=0):
      . * . * .
      . * * * .
      * * * * *
      * * * * *
      * . . . *

    Args:
        draw: PIL ImageDraw instance.
    """
    cx, cy = 58, 0
    c = COLOR_BIRTHDAY_CROWN
    # Row 0: points at columns 1, 3
    draw.point((cx + 1, cy + 0), fill=c)
    draw.point((cx + 3, cy + 0), fill=c)
    # Row 1: columns 1, 2, 3
    draw.point((cx + 1, cy + 1), fill=c)
    draw.point((cx + 2, cy + 1), fill=c)
    draw.point((cx + 3, cy + 1), fill=c)
    # Row 2: full row
    for i in range(5):
        draw.point((cx + i, cy + 2), fill=c)
    # Row 3: full row
    for i in range(5):
        draw.point((cx + i, cy + 3), fill=c)
    # Row 4: columns 0, 4 (feet of crown)
    draw.point((cx + 0, cy + 4), fill=c)
    draw.point((cx + 4, cy + 4), fill=c)


def _draw_birthday_sparkles(draw: ImageDraw.ImageDraw, date_str: str) -> None:
    """Draw deterministic sparkle pixels in the clock/date zone border area.

    Uses hash of date_str for deterministic but varied positions to avoid
    flicker between frames.

    Args:
        draw: PIL ImageDraw instance.
        date_str: Current date string (used for deterministic position hash).
    """
    h = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    sparkle_positions = [
        (abs(h) % 20 + 35, 0),        # top area, right of center
        (abs(h >> 4) % 15 + 2, 10),    # bottom of clock zone
        (abs(h >> 8) % 25 + 35, 18),   # near divider 1
    ]
    for x, y in sparkle_positions:
        if 0 <= x < 64 and 0 <= y < 64:
            draw.point((x, y), fill=(255, 255, 255))


def render_frame(
    state: DisplayState,
    fonts: dict,
    anim_frame: tuple[Image.Image, Image.Image] | None = None,
) -> Image.Image:
    """Render the dashboard state into a 64x64 RGB PIL Image.

    This function only renders from the provided state -- it does NOT
    fetch any data. Keep rendering and data collection separate.

    Args:
        state: Current display data (time string, date string).
        fonts: Dictionary with keys "small", "tiny" mapping
               to PIL ImageFont objects.
        anim_frame: Optional (bg_layer, fg_layer) RGBA tuple for weather zone (64x24 each).

    Returns:
        A 64x64 RGB PIL Image ready for pushing to the device.
    """
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Birthday color overrides -- golden clock, pink date on special days
    time_color = COLOR_BIRTHDAY_GOLD if state.is_birthday else COLOR_TIME
    date_color = COLOR_BIRTHDAY_ACCENT if state.is_birthday else COLOR_DATE

    # Clock time -- small font for compact 11px zone (still readable on LED)
    draw.text(
        (TEXT_X, CLOCK_ZONE.y + 1),
        state.time_str,
        font=fonts["small"],
        fill=time_color,
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

    # Birthday crown icon in top-right corner
    if state.is_birthday:
        _draw_birthday_crown(draw)

    # Date -- smaller text with color override on birthdays
    draw.text(
        (TEXT_X, DATE_ZONE.y),
        state.date_str,
        font=fonts["small"],
        fill=date_color,
    )

    # Birthday sparkle pixels -- deterministic positions based on date
    if state.is_birthday:
        _draw_birthday_sparkles(draw, state.date_str)

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

    # Weather zone -- temperature, high/low, rain with 3D layered animation
    render_weather_zone(draw, img, state, fonts, anim_layers=anim_frame)

    # Staleness indicator for weather data (orange dot at top-right of weather zone)
    if state.weather_stale and not state.weather_too_old:
        draw.point((62, WEATHER_ZONE.y + 1), fill=COLOR_STALE_INDICATOR)

    return img
