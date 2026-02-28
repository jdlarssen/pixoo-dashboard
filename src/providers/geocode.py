"""Reverse geocoding via OpenStreetMap Nominatim."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Resolve lat/lon to a city name via OpenStreetMap Nominatim."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
            headers={"User-Agent": "divoom-hub/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("village")
        )
    except (requests.RequestException, KeyError, ValueError):
        logger.debug("Reverse geocode failed for %s, %s", lat, lon)
        return None
