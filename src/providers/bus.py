"""Bus departure provider using the Entur JourneyPlanner v3 GraphQL API.

Fetches real-time bus departures from specific quay IDs and calculates
countdown minutes until each departure.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from src.config import (
    BUS_NUM_DEPARTURES,
    BUS_QUAY_DIRECTION1,
    BUS_QUAY_DIRECTION2,
    ENTUR_API_URL,
    ET_CLIENT_NAME,
)

logger = logging.getLogger(__name__)

# GraphQL query for estimated departures at a specific quay.
# timeRange: 3600 = look ahead 1 hour (3600 seconds).
# omitNonBoarding: true = skip departures where passengers can't board.
DEPARTURE_QUERY = """query($quayId: String!, $numDepartures: Int!) {
  quay(id: $quayId) {
    id
    name
    estimatedCalls(numberOfDepartures: $numDepartures, omitNonBoarding: true, timeRange: 3600) {
      expectedDepartureTime
      aimedDepartureTime
      realtime
      cancellation
      destinationDisplay {
        frontText
      }
      serviceJourney {
        line {
          publicCode
        }
      }
    }
  }
}"""


@dataclass
class BusDeparture:
    """A single bus departure with countdown and metadata."""

    minutes: int  # countdown minutes from now (clamped to >= 0)
    is_realtime: bool  # true if real-time data, false if scheduled
    destination: str  # e.g., "Sentrum" or "Strindheim via Lade"
    line: str  # e.g., "4" (public line code)


def fetch_departures(
    quay_id: str, num_departures: int = 2
) -> list[BusDeparture]:
    """Fetch upcoming departures from a specific quay.

    Args:
        quay_id: NSR quay identifier, e.g. "NSR:Quay:73154".
        num_departures: Number of departures to request.

    Returns:
        List of BusDeparture objects with countdown minutes.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status.
        KeyError: If the top-level response structure is unexpected.
    """
    # Request extra departures to compensate for cancelled ones being filtered out
    response = requests.post(
        ENTUR_API_URL,
        json={
            "query": DEPARTURE_QUERY,
            "variables": {
                "quayId": quay_id,
                "numDepartures": num_departures + 3,
            },
        },
        headers={"ET-Client-Name": ET_CLIENT_NAME},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    calls = data["data"]["quay"]["estimatedCalls"]
    now = datetime.now(tz=timezone.utc)

    departures = []
    for call in calls:
        if call.get("cancellation", False):
            continue  # Skip cancelled departures
        try:
            dep_time = datetime.fromisoformat(call["expectedDepartureTime"])
            minutes = int((dep_time - now).total_seconds() / 60)
            departures.append(
                BusDeparture(
                    minutes=max(0, minutes),
                    is_realtime=call["realtime"],
                    destination=call["destinationDisplay"]["frontText"],
                    line=call["serviceJourney"]["line"]["publicCode"],
                )
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Skipping malformed departure entry: %s", e)
            continue

    return departures[:num_departures]


def fetch_departures_safe(
    quay_id: str, num_departures: int = 2
) -> list[int] | None:
    """Fetch departures, returning countdown minutes or None on failure.

    Wraps fetch_departures() with error handling so API failures never
    crash the caller.

    Args:
        quay_id: NSR quay identifier.
        num_departures: Number of departures to request.

    Returns:
        List of countdown minutes on success, None on any failure.
    """
    try:
        departures = fetch_departures(quay_id, num_departures)
        return [d.minutes for d in departures]
    except Exception:
        logger.exception("Failed to fetch departures for %s", quay_id)
        return None


def fetch_quay_name(quay_id: str) -> str | None:
    """Fetch the human-readable name for a quay ID.

    Args:
        quay_id: NSR quay identifier, e.g. "NSR:Quay:73154".

    Returns:
        Quay name string on success, None on failure.
    """
    quay_name_query = "query($quayId: String!) { quay(id: $quayId) { name } }"
    try:
        response = requests.post(
            ENTUR_API_URL,
            json={
                "query": quay_name_query,
                "variables": {"quayId": quay_id},
            },
            headers={"ET-Client-Name": ET_CLIENT_NAME},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["data"]["quay"]["name"]
    except Exception:
        logger.exception("Failed to fetch quay name for %s", quay_id)
        return None


def fetch_bus_data() -> tuple[list[int] | None, list[int] | None]:
    """Fetch departure data for both directions at the configured stop.

    Returns:
        Tuple of (direction1_minutes, direction2_minutes).
        Each element is a list of countdown minutes or None on failure.
    """
    dir1 = fetch_departures_safe(BUS_QUAY_DIRECTION1, BUS_NUM_DEPARTURES)
    dir2 = fetch_departures_safe(BUS_QUAY_DIRECTION2, BUS_NUM_DEPARTURES)
    return (dir1, dir2)
