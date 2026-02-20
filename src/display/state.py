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
    bus_direction1: tuple[int, ...] | None = None  # e.g., (5, 12) or None
    bus_direction2: tuple[int, ...] | None = None  # e.g., (3, 8) or None

    @classmethod
    def from_now(
        cls,
        dt: datetime,
        bus_data: tuple[list[int] | None, list[int] | None] = (None, None),
    ) -> DisplayState:
        """Create a DisplayState from a datetime and optional bus data.

        Args:
            dt: Datetime to derive state from.
            bus_data: Tuple of (direction1_minutes, direction2_minutes).
                Each element is a list of countdown minutes or None.

        Returns:
            DisplayState with formatted time, date, and bus departure data.
        """
        return cls(
            time_str=format_time(dt),
            date_str=format_date_norwegian(dt),
            bus_direction1=tuple(bus_data[0]) if bus_data[0] else None,
            bus_direction2=tuple(bus_data[1]) if bus_data[1] else None,
        )
