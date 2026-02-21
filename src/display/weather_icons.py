"""Pixel art weather icons for the Pixoo 64 display.

Provides small (10px) weather condition icons drawn programmatically with PIL.
Icons are placed next to the clock digits in the clock zone.
"""

import math

from PIL import Image, ImageDraw

# MET symbol_code base -> icon group mapping
ICON_GROUP: dict[str, set[str]] = {
    "clear": {"clearsky", "fair"},
    "partcloud": {"partlycloudy"},
    "cloudy": {"cloudy"},
    "rain": {
        "rain", "lightrain", "heavyrain",
        "rainshowers", "lightrainshowers", "heavyrainshowers",
    },
    "sleet": {
        "sleet", "lightsleet", "heavysleet",
        "sleetshowers", "lightsleetshowers", "heavysleetshowers",
    },
    "snow": {
        "snow", "lightsnow", "heavysnow",
        "snowshowers", "lightsnowshowers", "heavysnowshowers",
    },
    "thunder": {
        "rainshowersandthunder", "heavyrainshowersandthunder",
        "lightrainshowersandthunder", "rainandthunder",
        "heavyrainandthunder", "lightrainandthunder",
        "sleetshowersandthunder", "heavysleetshowersandthunder",
        "lightsleetshowersandthunder", "sleetandthunder",
        "heavysleetandthunder", "lightsleetandthunder",
        "snowshowersandthunder", "heavysnowshowersandthunder",
        "lightsnowshowersandthunder", "snowandthunder",
        "heavysnowandthunder", "lightsnowandthunder",
        # Handle the known typo variants
        "lightssleetshowersandthunder", "lightssnowshowersandthunder",
    },
    "fog": {"fog"},
}

# Reverse lookup: base code -> group name
_CODE_TO_GROUP: dict[str, str] = {}
for _group, _codes in ICON_GROUP.items():
    for _code in _codes:
        _CODE_TO_GROUP[_code] = _group


def symbol_to_group(symbol_code: str) -> str:
    """Map MET symbol_code to icon group. Returns 'cloudy' as fallback."""
    base = (
        symbol_code
        .replace("_day", "")
        .replace("_night", "")
        .replace("_polartwilight", "")
    )
    return _CODE_TO_GROUP.get(base, "cloudy")


def _is_night(symbol_code: str) -> bool:
    """Check if symbol_code indicates nighttime."""
    return "_night" in symbol_code or "_polartwilight" in symbol_code


# ---------------------------------------------------------------------------
# Icon drawing functions (10x10 RGBA)
# ---------------------------------------------------------------------------

def _draw_sun(size: int) -> Image.Image:
    """Yellow sun with short ray lines."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = 2
    # Central circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 200, 50, 255))
    # Rays at 8 compass points
    ray_len = 2
    for angle_deg in range(0, 360, 45):
        rad = math.radians(angle_deg)
        x1 = cx + int((r + 1) * math.cos(rad))
        y1 = cy + int((r + 1) * math.sin(rad))
        x2 = cx + int((r + ray_len) * math.cos(rad))
        y2 = cy + int((r + ray_len) * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 50, 200))
    return img


def _draw_moon(size: int) -> Image.Image:
    """Hand-crafted crescent moon bitmap -- recognizable at 10px on LED.

    At 10x10 pixel resolution, mathematical circle/ellipse approaches produce
    rasterization artifacts (diagonal stripes, blobs). A hand-crafted pixel
    bitmap gives a clean, recognizable crescent shape.
    """
    # fmt: off
    # Hand-crafted 10x10 crescent moon (right-facing, wider at middle)
    #   . . . . # # . . . .
    #   . . # # # # . . . .
    #   . # # # # . . . . .
    #   . # # # . . . . . .
    #   # # # # . . . . . .
    #   # # # # . . . . . .
    #   . # # # . . . . . .
    #   . # # # # . . . . .
    #   . . # # # # . . . .
    #   . . . . # # . . . .
    pixels = [
        (4, 0), (5, 0),
        (2, 1), (3, 1), (4, 1), (5, 1),
        (1, 2), (2, 2), (3, 2), (4, 2),
        (1, 3), (2, 3), (3, 3),
        (0, 4), (1, 4), (2, 4), (3, 4),
        (0, 5), (1, 5), (2, 5), (3, 5),
        (1, 6), (2, 6), (3, 6),
        (1, 7), (2, 7), (3, 7), (4, 7),
        (2, 8), (3, 8), (4, 8), (5, 8),
        (4, 9), (5, 9),
    ]
    # fmt: on
    moon_color = (255, 220, 100, 255)  # warm golden yellow (like moonlight)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for x, y in pixels:
        if x < size and y < size:
            img.putpixel((x, y), moon_color)
    return img


def _draw_cloud(size: int, color: tuple = (200, 200, 210, 220)) -> Image.Image:
    """Simple overlapping ellipses cloud shape."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Two overlapping ovals
    draw.ellipse([1, 3, 6, 8], fill=color)
    draw.ellipse([3, 2, 9, 7], fill=color)
    return img


def _draw_cloud_with_drops(size: int) -> Image.Image:
    """Cloud with blue rain drops below."""
    img = _draw_cloud(size)
    draw = ImageDraw.Draw(img)
    # Blue drops below cloud
    drop_color = (80, 160, 255, 220)
    draw.point((2, 8), fill=drop_color)
    draw.point((5, 9), fill=drop_color)
    draw.point((7, 8), fill=drop_color)
    return img


def _draw_cloud_with_snow(size: int) -> Image.Image:
    """Cloud with white snowflake dots below."""
    img = _draw_cloud(size)
    draw = ImageDraw.Draw(img)
    snow_color = (255, 255, 255, 200)
    draw.point((2, 8), fill=snow_color)
    draw.point((4, 9), fill=snow_color)
    draw.point((6, 8), fill=snow_color)
    draw.point((8, 9), fill=snow_color)
    return img


def _draw_cloud_with_sleet(size: int) -> Image.Image:
    """Cloud with mixed blue/white drops below."""
    img = _draw_cloud(size)
    draw = ImageDraw.Draw(img)
    draw.point((2, 8), fill=(80, 160, 255, 220))   # rain
    draw.point((5, 9), fill=(255, 255, 255, 200))   # snow
    draw.point((7, 8), fill=(80, 160, 255, 220))    # rain
    return img


def _draw_cloud_with_lightning(size: int) -> Image.Image:
    """Cloud with yellow lightning bolt."""
    img = _draw_cloud(size)
    draw = ImageDraw.Draw(img)
    # Small zigzag bolt
    bolt_color = (255, 220, 50, 255)
    draw.line([(5, 7), (4, 8), (6, 8), (4, 10)], fill=bolt_color)
    return img


def _draw_fog(size: int) -> Image.Image:
    """Horizontal gray haze lines."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fog_color = (180, 180, 190, 160)
    for y in (2, 4, 6, 8):
        x_start = (y % 3)  # slight offset for organic feel
        draw.line([(x_start, y), (size - 1 - x_start, y)], fill=fog_color)
    return img


def _draw_partcloud_day(size: int) -> Image.Image:
    """Small sun peeking behind a cloud."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Sun in top-left
    draw.ellipse([0, 0, 4, 4], fill=(255, 200, 50, 200))
    # Cloud in front
    draw.ellipse([2, 3, 7, 8], fill=(200, 200, 210, 230))
    draw.ellipse([4, 2, 9, 7], fill=(200, 200, 210, 230))
    return img


def _draw_partcloud_night(size: int) -> Image.Image:
    """Small moon peeking behind a cloud.

    Uses a hand-crafted pixel bitmap for the mini crescent (same technique
    as ``_draw_moon``).  Ellipse math produces unrecognizable blobs at this
    scale.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # fmt: off
    # Mini crescent moon in top-left (hand-crafted pixel art)
    #   . . # #
    #   . # # .
    #   # # . .
    #   # # . .
    #   . # # .
    moon_pixels = [
                (2, 0), (3, 0),
        (1, 1), (2, 1),
        (0, 2), (1, 2),
        (0, 3), (1, 3),
        (1, 4), (2, 4),
    ]
    # fmt: on
    moon_color = (255, 220, 100, 255)  # warm golden yellow (matches _draw_moon)
    for x, y in moon_pixels:
        if x < size and y < size:
            img.putpixel((x, y), moon_color)
    # Cloud in front
    draw.ellipse([2, 3, 7, 8], fill=(200, 200, 210, 230))
    draw.ellipse([4, 2, 9, 7], fill=(200, 200, 210, 230))
    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_weather_icon(symbol_code: str, size: int = 10) -> Image.Image:
    """Get a pixel art weather icon for the given MET symbol_code.

    Args:
        symbol_code: MET weather symbol code (e.g. "clearsky_day", "rain").
        size: Icon size in pixels (default 10).

    Returns:
        RGBA PIL Image of the weather icon.
    """
    group = symbol_to_group(symbol_code)
    night = _is_night(symbol_code)

    if group == "clear":
        return _draw_moon(size) if night else _draw_sun(size)
    elif group == "partcloud":
        return _draw_partcloud_night(size) if night else _draw_partcloud_day(size)
    elif group == "cloudy":
        return _draw_cloud(size)
    elif group == "rain":
        return _draw_cloud_with_drops(size)
    elif group == "sleet":
        return _draw_cloud_with_sleet(size)
    elif group == "snow":
        return _draw_cloud_with_snow(size)
    elif group == "thunder":
        return _draw_cloud_with_lightning(size)
    elif group == "fog":
        return _draw_fog(size)
    else:
        return _draw_cloud(size)  # fallback
