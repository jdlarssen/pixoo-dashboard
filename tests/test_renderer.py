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
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
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
            bus_direction1=(120, 180, 240),
            bus_direction2=(65, 90, 120),
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
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
        )
        frame = render_frame(state, FONTS)
        assert frame.size == (64, 64)
        assert frame.mode == "RGB"

    def test_save_bus_dashboard(self):
        """Save a test frame with bus data to /tmp for visual inspection."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
        )
        frame = render_frame(state, FONTS)
        output_path = Path("/tmp/test_dashboard_bus.png")
        frame.save(output_path)
        assert output_path.exists(), "Failed to save bus dashboard image"


class TestWeatherZoneRendering:
    """Tests for weather zone rendering with weather data."""

    def test_weather_zone_renders_temperature(self):
        """Weather zone should show temperature text when weather_temp is set."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
        )
        frame = render_frame(state, FONTS)
        assert _has_non_black_pixels(frame, 44, 64), (
            "Weather zone (y=44..63) is all black -- no temperature rendered"
        )

    def test_weather_zone_placeholder_when_none(self):
        """Weather zone should show placeholder text when weather_temp is None."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=None,
            weather_symbol=None,
        )
        frame = render_frame(state, FONTS)
        assert _has_non_black_pixels(frame, 44, 64), (
            "Weather zone (y=44..63) is all black -- no placeholder rendered"
        )

    def test_negative_temperature_uses_blue_color(self):
        """Negative temperature should use blue color (not white)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=-5,
            weather_symbol="snow_day",
            weather_high=1,
            weather_low=-7,
            weather_precip_mm=0.0,
            weather_is_day=True,
        )
        frame = render_frame(state, FONTS)
        # Check weather zone for blue-ish pixels (R < G or R < B)
        found_blue = False
        for y in range(44, 55):  # temperature text area
            for x in range(64):
                r, g, b = frame.getpixel((x, y))
                if b > 100 and b > r and (r, g, b) != (0, 0, 0):
                    found_blue = True
                    break
            if found_blue:
                break
        assert found_blue, "No blue pixels found for negative temperature"

    def test_clock_icon_renders_with_weather_symbol(self):
        """Weather icon should appear in clock zone when weather_symbol is set."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="clearsky_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
        )
        # Render with and without weather symbol
        frame_with = render_frame(state, FONTS)
        state_without = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
        )
        frame_without = render_frame(state_without, FONTS)
        # Clock zone should differ (icon present vs absent)
        # Check the right side of clock zone where icon would be placed
        diff_found = False
        for y in range(0, 14):
            for x in range(40, 64):  # right side of clock zone
                if frame_with.getpixel((x, y)) != frame_without.getpixel((x, y)):
                    diff_found = True
                    break
            if diff_found:
                break
        assert diff_found, "No icon pixels found in clock zone right side"

    def test_clock_icon_absent_without_weather_symbol(self):
        """Clock zone right side should be empty when weather_symbol is None."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=None,
            weather_symbol=None,
        )
        frame = render_frame(state, FONTS)
        # Right side of clock zone (past the time text, ~x=45+) should be black
        all_black = True
        for y in range(0, 14):
            for x in range(50, 64):
                if frame.getpixel((x, y)) != (0, 0, 0):
                    all_black = False
                    break
            if not all_black:
                break
        assert all_black, "Clock zone right side has unexpected pixels without weather symbol"

    def test_render_frame_accepts_anim_frame(self):
        """render_frame should accept anim_frame parameter without error."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="rain_day",
            weather_high=10,
            weather_low=5,
            weather_precip_mm=2.1,
            weather_is_day=True,
        )
        # Create a mock animation frame (64x20 RGBA)
        anim_frame = Image.new("RGBA", (64, 20), (80, 160, 255, 30))
        frame = render_frame(state, FONTS, anim_frame=anim_frame)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
        assert frame.mode == "RGB"

    def test_rain_indicator_with_precipitation(self):
        """Weather zone should show rain indicator when precip > 0."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="rain_day",
            weather_high=10,
            weather_low=5,
            weather_precip_mm=2.5,
            weather_is_day=True,
        )
        frame = render_frame(state, FONTS)
        # Lower part of weather zone (y=55+) should have rain text pixels
        assert _has_non_black_pixels(frame, 55, 64), (
            "No rain indicator pixels in lower weather zone"
        )

    def test_save_weather_dashboard(self):
        """Save a test frame with full weather data to /tmp for visual inspection."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.5,
            weather_is_day=True,
        )
        frame = render_frame(state, FONTS)
        output_path = Path("/tmp/test_dashboard_weather.png")
        frame.save(output_path)
        assert output_path.exists(), "Failed to save weather dashboard image"
