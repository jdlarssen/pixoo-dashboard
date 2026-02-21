"""Tests for the 64x64 dashboard renderer."""

from pathlib import Path

from PIL import Image

from src.config import FONT_DIR, FONT_SMALL, FONT_TINY
from src.display.fonts import load_fonts
from src.display.layout import BUS_ZONE, COLOR_STALE_INDICATOR, WEATHER_ZONE
from src.display.renderer import render_frame
from src.display.state import DisplayState

# Load actual fonts for integration testing
_raw_fonts = load_fonts(FONT_DIR)
FONTS = {
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
        """Clock zone (y=0 to y=10) should contain non-black pixels (time text)."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 0, 11), (
            "Clock zone (y=0..10) is all black -- no time text rendered"
        )

    def test_date_region_has_pixels(self):
        """Date zone (y=11 to y=18) should contain non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 11, 19), (
            "Date zone (y=11..18) is all black -- no date text rendered"
        )

    def test_divider_1_exists(self):
        """Divider line at y=19 should have non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _row_has_non_black_pixels(frame, 19), (
            "Divider 1 at y=19 is all black -- no divider line drawn"
        )

    def test_divider_2_exists(self):
        """Divider line at y=39 should have non-black pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _row_has_non_black_pixels(frame, 39), (
            "Divider 2 at y=39 is all black -- no divider line drawn"
        )

    def test_bus_placeholder_has_pixels(self):
        """Bus zone (y=20 to y=38) should contain placeholder text pixels.

        Even with no bus data (None), the bus zone should render dashes.
        """
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 20, 39), (
            "Bus zone (y=20..38) is all black -- no bus zone text rendered"
        )

    def test_weather_placeholder_has_pixels(self):
        """Weather zone (y=40 to y=63) should contain placeholder text pixels."""
        frame = render_frame(TEST_STATE, FONTS)
        assert _has_non_black_pixels(frame, 40, 64), (
            "Weather zone (y=40..63) is all black -- no placeholder text rendered"
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
        assert _has_non_black_pixels(frame, 20, 39), (
            "Bus zone (y=20..38) is all black -- no bus data rendered"
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
        assert _has_non_black_pixels(frame, 20, 39), (
            "Bus zone (y=20..38) is all black -- dashes not rendered for None data"
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
        assert _has_non_black_pixels(frame, 20, 39)

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
        assert _has_non_black_pixels(frame, 20, 39)

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
        assert _has_non_black_pixels(frame, 20, 39)

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
        assert _has_non_black_pixels(frame, 20, 39)

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
        assert _has_non_black_pixels(frame, 40, 64), (
            "Weather zone (y=40..63) is all black -- no temperature rendered"
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
        assert _has_non_black_pixels(frame, 40, 64), (
            "Weather zone (y=40..63) is all black -- no placeholder rendered"
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
        for y in range(40, 52):  # temperature text area
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
        for y in range(0, 11):
            for x in range(30, 64):  # right side of clock zone (smaller font = icon closer)
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
        for y in range(0, 11):
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
        # Create mock animation layers (bg + fg, each 64x24 RGBA)
        bg_layer = Image.new("RGBA", (64, 24), (80, 160, 255, 30))
        fg_layer = Image.new("RGBA", (64, 24), (80, 160, 255, 20))
        frame = render_frame(state, FONTS, anim_frame=(bg_layer, fg_layer))
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
        # Lower part of weather zone (y=51+) should have rain text pixels
        assert _has_non_black_pixels(frame, 51, 64), (
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


class TestStalenessIndicator:
    """Tests for the staleness indicator dot rendering."""

    def test_bus_staleness_dot_renders_when_stale(self):
        """Orange dot appears at (62, BUS_ZONE.y+1) when bus_stale=True and bus_too_old=False."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
            bus_stale=True,
            bus_too_old=False,
        )
        frame = render_frame(state, FONTS)
        pixel = frame.getpixel((62, BUS_ZONE.y + 1))
        assert pixel == COLOR_STALE_INDICATOR, (
            f"Expected orange dot {COLOR_STALE_INDICATOR} at (62, {BUS_ZONE.y + 1}), got {pixel}"
        )

    def test_bus_staleness_dot_absent_when_not_stale(self):
        """No orange dot when bus_stale=False."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
            bus_stale=False,
        )
        frame = render_frame(state, FONTS)
        pixel = frame.getpixel((62, BUS_ZONE.y + 1))
        assert pixel != COLOR_STALE_INDICATOR, (
            "Orange dot should not appear when bus_stale=False"
        )

    def test_bus_staleness_dot_absent_when_too_old(self):
        """No orange dot when bus_too_old=True (suppresses the dot -- shows dash placeholders instead)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            bus_stale=True,
            bus_too_old=True,
        )
        frame = render_frame(state, FONTS)
        pixel = frame.getpixel((62, BUS_ZONE.y + 1))
        assert pixel != COLOR_STALE_INDICATOR, (
            "Orange dot should not appear when bus_too_old=True"
        )

    def test_weather_staleness_dot_renders_when_stale(self):
        """Orange dot appears at (62, WEATHER_ZONE.y+1) when weather_stale=True and weather_too_old=False."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            weather_stale=True,
            weather_too_old=False,
        )
        frame = render_frame(state, FONTS)
        pixel = frame.getpixel((62, WEATHER_ZONE.y + 1))
        assert pixel == COLOR_STALE_INDICATOR, (
            f"Expected orange dot {COLOR_STALE_INDICATOR} at (62, {WEATHER_ZONE.y + 1}), got {pixel}"
        )


class TestMessageRendering:
    """Tests for Discord message rendering, including emoji/Unicode safety."""

    def test_ascii_message_renders_without_crash(self):
        """Plain ASCII message should render pixels in the weather zone."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            message_text="Hello!",
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)

    def test_emoji_message_does_not_crash(self):
        """Message with emoji must NOT crash the renderer (was UnicodeEncodeError)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            message_text="Klaebo vant! \U0001f604",
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)

    def test_all_emoji_message_renders_empty(self):
        """Message that is ALL emoji should render without crash (empty after strip)."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            message_text="\U0001f604\U0001f389\U0001f525",
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)

    def test_mixed_emoji_and_text_renders(self):
        """Mixed emoji + text should render the text portion without crash."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            message_text="\U0001f3c6 Gull! \U0001f1f3\U0001f1f4",
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)

    def test_norwegian_chars_in_message(self):
        """Norwegian characters (within Latin-1) should render fine."""
        state = DisplayState(
            time_str="14:32",
            date_str="lor 21. mar",
            weather_temp=8,
            weather_symbol="partlycloudy_day",
            weather_high=12,
            weather_low=3,
            weather_precip_mm=0.0,
            weather_is_day=True,
            message_text="Kl\u00e6bo v\u00e6rt b\u00e5de gull",
        )
        frame = render_frame(state, FONTS)
        assert isinstance(frame, Image.Image)
        assert frame.size == (64, 64)
