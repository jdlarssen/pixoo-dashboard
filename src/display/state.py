"""Display state model for the Divoom Hub dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.providers.clock import format_date_norwegian, format_time


@dataclass
class DisplayState:
    """Holds the current data to render on the display.

    Supports equality comparison via dataclass default __eq__,
    enabling the dirty flag pattern -- only re-render when state changes.
    """

    time_str: str  # e.g., "14:32"
    date_str: str  # e.g., "tor 20. feb"

    @classmethod
    def from_now(cls, dt: datetime) -> DisplayState:
        """Create a DisplayState from a datetime.

        Args:
            dt: Datetime to derive state from.

        Returns:
            DisplayState with formatted time and date strings.
        """
        return cls(
            time_str=format_time(dt),
            date_str=format_date_norwegian(dt),
        )
