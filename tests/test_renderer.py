"""Tests for the 64x64 dashboard renderer."""

from pathlib import Path

from PIL import Image

from src.config import FONT_DIR, FONT_LARGE, FONT_SMALL, FONT_TINY
from src.display.fonts import load_fonts
from src.display.renderer import render_frame
from src.display.state import DisplayState

# Load actual fonts for integration testing
_raw_fonts = load_fonts(FONT_DIR)
FONTS = {
    "large": _raw_fonts[FONT_LARGE],
    "small": _raw_fonts[FONT_SMALL],
    "tiny": _raw_fonts[FONT_TINY],
}

# Test state with Norwegian date including oe character
TEST_STATE = DisplayState(
    time_str="14:32",
    date_str="l\u00f8r 21. mar",
)


def _has_non_black_pixels(img: Image.Image, y_start: int, y_end: int) -> bool:
    """Check if any pixels in the given row range are non-black."""
    for y in range(y_start, y_end):
        for x in range(64):
            if img.getpixel((x, y)) != (0, 0, 0):
                return True
    return False


def _row_has_non_black_pixels(img: Image.Image, y: int) -> bool:
    """Check if a specific row contains any non-black pixels."""
    for x in range(64):
        if img.getpixel((x, y)) != (0, 0, 0):
            return True
    return False


class TestRenderFrame:
    """Tests for render_frame()."""

    def test_returns_64x64_rgb_image(self):
        frame = render_frame(TEST_STATE, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert frame.mode == "RGB"

    def test_clock_region_has_pixels(self):
        """Clock zone (y=0 to y=13) should contain non-black pixels (white text)."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 0, 14), (
            "Clock zone (y=0..13) is all black -- no time text rendered"
        )

    def test_date_region_has_pixels(self):
        """Date zone (y=14 to y=22) should contain non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 14, 23), (
            "Date zone (y=14..22) is all black -- no date text rendered"
        )

    def test_divider_1_exists(self):
        """Divider line at y=23 should have non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _row_has_non_black_pixels(frame, 23), (
            "Divider 1 at y=23 is all black -- no divider line drawn"
        )

    def test_divider_2_exists(self):
        """Divider line at y=43 should have non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _row_has_non_black_pixels(frame, 43), (
            "Divider 2 at y=43 is all black -- no divider line drawn"
        )

    def test_bus_placeholder_has_pixels(self):
        """Bus zone (y=24 to y=42) should contain placeholder text pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 24, 43), (
            "Bus zone (y=24..42) is all black -- no placeholder text rendered"
        )

    def test_weather_placeholder_has_pixels(self):
        """Weather zone (y=44 to y=63) should contain placeholder text pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 44, 64), (
            "Weather zone (y=44..63) is all black -- no placeholder text rendered"
        )

    def test_save_test_dashboard(self):
        """Save a test frame to /tmp for visual inspection."""
        frame = render_frame(TEST_STATE, FONTS)
        output_path = Path("/tmp/test_dashboard.png")
        frame.save(output_path)
        assert output_path.exists(), "Failed to save test dashboard image"
