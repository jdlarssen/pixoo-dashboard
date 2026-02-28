"""Norwegian clock and date formatting provider."""

from datetime import datetime

# Norwegian day abbreviations (Monday=0 through Sunday=6)
# Note: Saturday (l\u00f8rdag) and Sunday (s\u00f8ndag) contain \u00f8 (oe)
DAYS_NO = ["man", "tir", "ons", "tor", "fre", "l\u00f8r", "s\u00f8n"]

# Norwegian month abbreviations (January=0 through December=11)
# None of the abbreviated month names contain special characters
MONTHS_NO = [
    "jan",
    "feb",
    "mar",
    "apr",
    "mai",
    "jun",
    "jul",
    "aug",
    "sep",
    "okt",
    "nov",
    "des",
]


def format_time(dt: datetime) -> str:
    """Format time as HH:MM in 24-hour format.

    Args:
        dt: Datetime to format.

    Returns:
        Time string like "14:32" or "09:05".
    """
    return dt.strftime("%H:%M")


def format_date_norwegian(dt: datetime) -> str:
    """Format date as Norwegian abbreviated string.

    Args:
        dt: Datetime to format.

    Returns:
        Date string like "tor 20. feb" or "l\u00f8r 21. mar".
    """
    day_name = DAYS_NO[dt.weekday()]
    month_name = MONTHS_NO[dt.month - 1]
    return f"{day_name} {dt.day}. {month_name}"
