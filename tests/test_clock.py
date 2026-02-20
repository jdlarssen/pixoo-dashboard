"""Tests for Norwegian clock/date formatting and DisplayState."""

from datetime import datetime

from src.display.state import DisplayState
from src.providers.clock import format_date_norwegian, format_time


class TestFormatTime:
    """Tests for format_time()."""

    def test_morning_with_leading_zero(self):
        dt = datetime(2026, 2, 20, 9, 5, 0)
        assert format_time(dt) == "09:05"

    def test_afternoon(self):
        dt = datetime(2026, 2, 20, 14, 32, 0)
        assert format_time(dt) == "14:32"

    def test_midnight(self):
        dt = datetime(2026, 2, 20, 0, 0, 0)
        assert format_time(dt) == "00:00"

    def test_end_of_day(self):
        dt = datetime(2026, 2, 20, 23, 59, 59)
        assert format_time(dt) == "23:59"


class TestFormatDateNorwegian:
    """Tests for format_date_norwegian()."""

    def test_thursday_february(self):
        # Thursday Feb 19, 2026 (Feb 20 is Friday)
        dt = datetime(2026, 2, 19)
        assert format_date_norwegian(dt) == "tor 19. feb"

    def test_saturday_with_oe(self):
        # Saturday March 21, 2026 -- "l\u00f8r" must contain oe
        dt = datetime(2026, 3, 21)
        result = format_date_norwegian(dt)
        assert result == "l\u00f8r 21. mar"

    def test_sunday_with_oe(self):
        # Sunday January 1, 2026 -- "s\u00f8n" must contain oe
        dt = datetime(2026, 1, 4)  # Jan 4, 2026 is a Sunday
        result = format_date_norwegian(dt)
        assert result == "s\u00f8n 4. jan"

    def test_wednesday_december(self):
        # Wednesday December 31, 2025
        dt = datetime(2025, 12, 31)
        assert format_date_norwegian(dt) == "ons 31. des"

    def test_saturday_contains_unicode_oe(self):
        """Verify 'l\u00f8r' contains the actual Unicode oe character (U+00F8), not ASCII 'o'."""
        dt = datetime(2026, 3, 21)  # Saturday
        result = format_date_norwegian(dt)
        day_abbrev = result.split(" ")[0]
        assert "\u00f8" in day_abbrev, (
            f"Saturday abbreviation '{day_abbrev}' does not contain "
            f"Unicode oe (U+00F8) -- got ASCII 'o' instead?"
        )

    def test_sunday_contains_unicode_oe(self):
        """Verify 's\u00f8n' contains the actual Unicode oe character (U+00F8), not ASCII 'o'."""
        dt = datetime(2026, 1, 4)  # Sunday
        result = format_date_norwegian(dt)
        day_abbrev = result.split(" ")[0]
        assert "\u00f8" in day_abbrev, (
            f"Sunday abbreviation '{day_abbrev}' does not contain "
            f"Unicode oe (U+00F8) -- got ASCII 'o' instead?"
        )

    def test_single_digit_day(self):
        """Day number should not have leading zero."""
        dt = datetime(2026, 1, 4)
        result = format_date_norwegian(dt)
        # Should be "s\u00f8n 4. jan", not "s\u00f8n 04. jan"
        assert " 4. " in result


class TestDisplayState:
    """Tests for DisplayState equality and factory method."""

    def test_equal_states(self):
        s1 = DisplayState(time_str="14:32", date_str="tor 20. feb")
        s2 = DisplayState(time_str="14:32", date_str="tor 20. feb")
        assert s1 == s2

    def test_different_time(self):
        s1 = DisplayState(time_str="14:32", date_str="tor 20. feb")
        s2 = DisplayState(time_str="14:33", date_str="tor 20. feb")
        assert s1 != s2

    def test_different_date(self):
        s1 = DisplayState(time_str="14:32", date_str="tor 20. feb")
        s2 = DisplayState(time_str="14:32", date_str="fre 21. feb")
        assert s1 != s2

    def test_from_now(self):
        dt = datetime(2026, 2, 19, 14, 32, 0)
        state = DisplayState.from_now(dt)
        assert state.time_str == "14:32"
        assert state.date_str == "tor 19. feb"

    def test_from_now_saturday(self):
        dt = datetime(2026, 3, 21, 9, 0, 0)
        state = DisplayState.from_now(dt)
        assert state.time_str == "09:00"
        assert state.date_str == "l\u00f8r 21. mar"
