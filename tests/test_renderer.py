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
        """Bus zone (y=24 to y=42) should contain placeholder text pixels.

        Even with no bus data (None), the bus zone should render dashes.
        """
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 24, 43), (
            "Bus zone (y=24..42) is all black -- no bus zone text rendered"
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


class TestBusZoneRendering:
    """Tests for bus zone rendering with departure data."""

    def test_bus_zone_with_data_has_colored_pixels(self):
        """Bus zone should contain non-black pixels when bus data is present."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12),
            bus_direction2=(3, 8),
        )
        frame = render_frame(state, FONTS)
        assert _has_non_black_pixels(frame, 24, 43), (
            "Bus zone (y=24..42) is all black -- no bus data rendered"
        )

    def test_bus_zone_with_none_data_renders_dashes(self):
        """Bus zone should render without crashing when bus data is None."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=None,
            bus_direction2=None,
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert frame.mode == "RGB"
        # Should still have pixels (dashes rendered in dim gray)
        assert _has_non_black_pixels(frame, 24, 43), (
            "Bus zone (y=24..42) is all black -- dashes not rendered for None data"
        )

    def test_bus_zone_with_partial_data(self):
        """Bus zone renders when one direction has data, other is None."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12),
            bus_direction2=None,
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert _has_non_black_pixels(frame, 24, 43)

    def test_bus_zone_with_zero_minutes(self):
        """Bus zone handles 0 minutes (bus arriving now) correctly."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(0, 5),
            bus_direction2=(0, 0),
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert _has_non_black_pixels(frame, 24, 43)

    def test_bus_zone_with_empty_tuple(self):
        """Bus zone handles empty tuple (API returned 0 departures)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(),
            bus_direction2=(),
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert _has_non_black_pixels(frame, 24, 43)

    def test_bus_zone_with_long_waits(self):
        """Bus zone handles large countdown numbers (60+ minutes)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(120, 180),
            bus_direction2=(65, 90),
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert _has_non_black_pixels(frame, 24, 43)

    def test_rendered_image_still_64x64_rgb(self):
        """Full dashboard with bus data is still 64x64 RGB."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12),
            bus_direction2=(3, 8),
        )
        frame = render_frame(state, FONTS)
        assert frame.size == (64, 64)
        assert frame.mode == "RGB"

    def test_save_bus_dashboard(self):
        """Save a test frame with bus data to /tmp for visual inspection."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12),
            bus_direction2=(3, 8),
        )
        frame = render_frame(state, FONTS)
        output_path = Path("/tmp/test_dashboard_bus.png")
        frame.save(output_path)
        assert output_path.exists(), "Failed to save bus dashboard image"
