"""Shared text sanitization utilities for BDF bitmap font rendering.

BDF fonts only support Latin-1 (code points 0-255). Characters outside
this range (emoji, CJK, etc.) cause UnicodeEncodeError in PIL's
font.getbbox(). These functions strip them before text reaches the renderer.
"""

from __future__ import annotations

import re


def sanitize_for_bdf(text: str) -> str | None:
    """Strip characters that BDF bitmap fonts cannot render.

    Removes characters outside Latin-1, collapses whitespace, and strips
    leading/trailing whitespace.

    Args:
        text: Raw message text (may contain emoji, Unicode, etc.).

    Returns:
        Sanitized text with only Latin-1 characters, or None if nothing
        renderable remains. Consecutive whitespace is collapsed.
    """
    cleaned = "".join(ch for ch in text if ord(ch) <= 255)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


def strip_non_latin1(text: str) -> str:
    """Remove characters outside Latin-1 range that BDF fonts cannot render.

    Unlike :func:`sanitize_for_bdf`, this does not collapse whitespace or
    return None for empty results. It is a lightweight defensive filter.

    Args:
        text: Text that may contain non-Latin-1 characters.

    Returns:
        Text with only Latin-1 characters (code points 0-255).
    """
    return "".join(ch for ch in text if ord(ch) <= 255)
