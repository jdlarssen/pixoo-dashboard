"""Tests for BDF font conversion and Norwegian character rendering."""

from pathlib import Path

from PIL import Image, ImageDraw

from src.config import FONT_DIR
from src.display.fonts import load_fonts

EXPECTED_FONTS = {"4x6", "5x8", "7x13"}


def test_load_fonts_returns_expected_keys():
    """load_fonts() returns a dict with keys for all three font sizes."""
    fonts = load_fonts(FONT_DIR)
    assert set(fonts.keys()) == EXPECTED_FONTS


def test_fonts_render_time_digits():
    """Each font can render the string '14:32' without error."""
    fonts = load_fonts(FONT_DIR)
    for _name, font in fonts.items():
        img = Image.new("RGB", (64, 64), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((2, 2), "14:32", font=font, fill=(255, 255, 255))
        # If we get here without error, the font can render digits


def test_norwegian_characters_render_visible_pixels():
    """Norwegian characters (ae, oe, aa) render as non-black pixels.

    This is the critical test for DISP-02. If these characters silently
    fail to render, the entire font strategy is invalid.
    """
    fonts = load_fonts(FONT_DIR)
    test_strings = [
        "\u00f8",           # oe (lowercase, U+00F8) -- as in "lor"
        "\u00c5",           # Aa (uppercase, U+00C5)
        "\u00e5",           # aa (lowercase, U+00E5)
        "\u00e6",           # ae (lowercase, U+00E6)
        "\u00c6",           # Ae (uppercase, U+00C6)
        "l\u00f8r 21. mar",  # Saturday with oe
        "bl\u00e5b\u00e6r",  # "blueberry" with aa and ae
    ]

    for name, font in fonts.items():
        for test_str in test_strings:
            img = Image.new("RGB", (64, 64), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((2, 2), test_str, font=font, fill=(255, 255, 255))

            # Check that at least some pixels are non-black
            pixels = list(img.getdata())
            non_black = [p for p in pixels if p != (0, 0, 0)]
            assert len(non_black) > 0, (
                f"Font '{name}' rendered '{test_str}' as all black pixels -- "
                f"character not in font glyph set"
            )


def test_save_norwegian_test_image():
    """Save a test image with Norwegian text to /tmp for visual inspection."""
    fonts = load_fonts(FONT_DIR)
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = 0
    # Use small font for the test image to fit more text
    font_small = fonts["5x8"]
    font_large = fonts["7x13"]

    # Clock-style time in large font
    draw.text((2, y), "14:32", font=font_large, fill=(255, 255, 255))
    y += 14

    # Norwegian date with oe
    draw.text((2, y), "l\u00f8r 21. mar", font=font_small, fill=(180, 180, 180))
    y += 10

    # Test aa
    draw.text((2, y), "\u00c5lesund", font=font_small, fill=(180, 180, 180))
    y += 10

    # Test ae
    draw.text((2, y), "bl\u00e5b\u00e6r", font=font_small, fill=(180, 180, 180))
    y += 10

    # All special chars together
    draw.text((2, y), "\u00e6\u00f8\u00e5\u00c6\u00d8\u00c5", font=font_small, fill=(255, 255, 100))

    output_path = Path("/tmp/font_test.png")  # noqa: S108
    img.save(output_path)
    assert output_path.exists()
