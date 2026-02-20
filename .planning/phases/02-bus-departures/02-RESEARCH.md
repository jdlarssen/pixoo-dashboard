# Phase 2: Bus Departures - Research

**Researched:** 2026-02-20
**Domain:** Entur JourneyPlanner GraphQL API, real-time bus departures, countdown calculation, 64x19px bus zone rendering
**Confidence:** HIGH

## Summary

Phase 2 adds live bus departure data to the existing 64x64 dashboard by querying the Entur JourneyPlanner v3 GraphQL API. The API is free, open (NLOD license), requires no authentication beyond an `ET-Client-Name` identification header, and returns real-time departure data including `expectedDepartureTime` as ISO 8601 timestamps. Direction filtering is achieved by querying individual **quay** IDs rather than the stop place -- each physical platform at a bus stop has its own quay ID (e.g., `NSR:Quay:XXXXX`), and each quay serves a single direction. This means the implementation queries two quay IDs (one per direction: Sentrum and Lade) rather than querying the stop place and filtering afterward.

The technical implementation is straightforward: a Python provider module uses the `requests` library (already installed as a transitive dependency of `pixoo`) to POST GraphQL queries to `https://api.entur.io/journey-planner/v3/graphql`, parses the ISO 8601 `expectedDepartureTime` with `datetime.fromisoformat()` (fully supported in Python 3.14), calculates countdown minutes as `(departure_time - now).total_seconds() / 60`, and returns structured departure data. The existing `DisplayState` dataclass is extended with bus departure fields, and the renderer draws two lines of bus data in the 64x19px bus zone using the 4x6 ("tiny") and 5x8 ("small") fonts already loaded. The 60-second refresh cycle runs independently from the 1-second display check loop.

**Primary recommendation:** Use `requests` to call the Entur JourneyPlanner v3 GraphQL API directly with quay-level queries. Do NOT use the `enturclient` library (last updated 2022, requires `aiohttp`/async which the project does not use). Query two specific quay IDs (one per direction) with `numberOfDepartures: 2` each.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Compact stacked layout: one line per direction, each line has direction label + 2 countdown numbers
- Two content lines total within the 19px tall bus zone
- Direction 1 (Sentrum) on top, direction 2 (Lade) below
- Arrow glyph + single letter: arrow + "S" for Sentrum, arrow + "L" for Lade
- Each direction gets a distinct color (different from each other) for the arrow+letter label
- Format example: `>S  5  12` and `<L  3  8`
- Bare numbers only, no "min" or "m" suffix -- context makes minutes obvious
- Two countdowns per line separated by spacing (next departure + following departure)
- Stop ID: `NSR:StopPlace:42686` (Ladeveien, Trondheim)
- Single stop serves both directions -- use Entur direction/quay data to split departures
- Stop ID and direction config should be configurable via config file or environment variable, not hardcoded

### Claude's Discretion
- Separator between direction lines (thin divider vs spacing -- pick what looks best in 19px)
- Visual distinction between first and second departure (brightness, color, or same style)
- Vertical alignment of content lines within bus zone (centered vs top-aligned)
- Arrow glyph style (filled triangle vs line arrow -- pick what renders cleanly in BDF font)
- Direction label colors (pick two distinct, readable colors for LED display)
- "Now" indicator for 0-minute countdown (e.g., "Na" vs "0")
- No-bus empty state (dashes, blank, or message -- pick best approach for the display)
- Long wait handling (cap at 60+, show raw number, or switch to clock time)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUS-01 | Show next 2 departures from Ladeveien -- direction 1 | Query quay ID for direction 1 (Sentrum) via Entur JourneyPlanner v3 GraphQL API with `numberOfDepartures: 2`. Quay ID must be looked up from `NSR:StopPlace:42686` via stoppested.entur.org or a one-time GraphQL query. |
| BUS-02 | Show next 2 departures from Ladeveien -- direction 2 | Query quay ID for direction 2 (Lade) via same API with `numberOfDepartures: 2`. Same lookup process as BUS-01. |
| BUS-03 | Countdown format ("5 min" instead of "14:35") | Parse `expectedDepartureTime` (ISO 8601 with timezone) using `datetime.fromisoformat()`, subtract `datetime.now(tz=timezone.utc)`, convert `timedelta.total_seconds() / 60` to integer minutes. Display as bare number per user decision. |
| BUS-05 | 60-second refresh cycle | Timer-based fetch in the main loop. Track `last_bus_fetch` timestamp, re-fetch when 60 seconds have elapsed. Entur rate limit is per-minute quota; 1 request per 60 seconds is well within limits. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.5 | HTTP POST to Entur GraphQL API | Already installed (transitive dep of pixoo). Synchronous, simple, fits the project's synchronous main loop. No need for async. |
| datetime (stdlib) | Python 3.14 | ISO 8601 parsing + countdown math | `datetime.fromisoformat()` fully supports ISO 8601 with timezone offsets since Python 3.11. No third-party date library needed. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | Python 3.14 | Parse GraphQL JSON responses | `requests.Response.json()` handles this automatically. |
| logging (stdlib) | Python 3.14 | Log API errors and fetch cycles | Follow existing pattern from `src/main.py` and `src/device/pixoo_client.py`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` (direct GraphQL) | `enturclient` library (hfurubotten) | enturclient adds aiohttp async dependency, last released 2022 (v0.2.4), adds complexity for no benefit. Direct `requests` POST is ~15 lines and fully synchronous. |
| `requests` (direct GraphQL) | `gql` (graphql-core client) | Overkill for a single static query. gql adds schema validation/introspection we don't need. Raw POST is simpler. |
| `datetime.fromisoformat()` | `ciso8601` or `python-dateutil` | Third-party libraries are faster but unnecessary. We parse 4 timestamps per refresh (2 per direction x 2 directions). Performance is irrelevant at this scale. |
| Quay-level queries (2 queries) | StopPlace query + client-side filter | StopPlace query returns all departures from all quays, requiring client-side direction logic. Quay-level queries are cleaner: the API does the filtering. Two small queries is simpler than one large query with post-processing. |

**Installation:**
```bash
# No new dependencies needed -- requests is already installed via pixoo
pip install requests  # Already present (v2.32.5)
```

## Architecture Patterns

### Recommended Project Structure (additions to existing)
```
src/
├── providers/
│   ├── clock.py          # (existing) Norwegian clock formatting
│   └── bus.py            # (NEW) Entur API client + departure data
├── display/
│   ├── state.py          # (MODIFY) Add bus departure fields to DisplayState
│   ├── renderer.py       # (MODIFY) Add bus zone rendering
│   └── layout.py         # (MODIFY) Add bus zone color constants
├── config.py             # (MODIFY) Add bus stop/quay configuration
└── main.py               # (MODIFY) Add bus fetch to main loop
```

### Pattern 1: Bus Provider (Data Fetcher)

**What:** A provider module that queries the Entur API and returns structured departure data. Follows the same provider pattern as `clock.py` -- pure data, no rendering.

**When to use:** Every 60 seconds in the main loop.

**Example:**
```python
# Source: Entur JourneyPlanner v3 API docs + requests library
import requests
from datetime import datetime, timezone
from dataclasses import dataclass

ENTUR_API_URL = "https://api.entur.io/journey-planner/v3/graphql"
ET_CLIENT_NAME = "jdl-divoomhub"

DEPARTURE_QUERY = """
{
  quay(id: "%s") {
    id
    name
    estimatedCalls(numberOfDepartures: %d, omitNonBoarding: true) {
      expectedDepartureTime
      aimedDepartureTime
      realtime
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
}
"""

@dataclass
class BusDeparture:
    minutes: int          # countdown minutes from now
    is_realtime: bool     # true if real-time data, false if scheduled
    destination: str      # e.g., "Sentrum" or "Lade"
    line: str             # e.g., "4" (public code)

def fetch_departures(quay_id: str, num_departures: int = 2) -> list[BusDeparture]:
    query = DEPARTURE_QUERY % (quay_id, num_departures)
    headers = {"ET-Client-Name": ET_CLIENT_NAME}

    response = requests.post(
        ENTUR_API_URL,
        json={"query": query},
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    calls = data["data"]["quay"]["estimatedCalls"]
    now = datetime.now(tz=timezone.utc)

    departures = []
    for call in calls:
        dep_time = datetime.fromisoformat(call["expectedDepartureTime"])
        minutes = int((dep_time - now).total_seconds() / 60)
        departures.append(BusDeparture(
            minutes=max(0, minutes),
            is_realtime=call["realtime"],
            destination=call["destinationDisplay"]["frontText"],
            line=call["serviceJourney"]["line"]["publicCode"],
        ))
    return departures
```

### Pattern 2: DisplayState Extension

**What:** Extend the existing `DisplayState` dataclass with bus departure data so the renderer can draw it.

**When to use:** DisplayState is the single source of truth for what appears on screen. Bus data must flow through it.

**Example:**
```python
@dataclass
class DisplayState:
    time_str: str
    date_str: str
    bus_direction1: list[int] | None = None  # [5, 12] or None if no data
    bus_direction2: list[int] | None = None  # [3, 8] or None if no data
```

### Pattern 3: Independent Refresh Timers

**What:** The main loop checks time every 1 second (for the clock dirty flag) but fetches bus data only every 60 seconds using a separate timer.

**When to use:** To decouple clock update frequency from bus API refresh frequency.

**Example:**
```python
import time

BUS_REFRESH_INTERVAL = 60  # seconds

def main_loop(client, fonts):
    last_state = None
    last_bus_fetch = 0.0
    bus_data = (None, None)  # (direction1_minutes, direction2_minutes)

    while True:
        now_mono = time.monotonic()

        # Fetch bus data every 60 seconds
        if now_mono - last_bus_fetch >= BUS_REFRESH_INTERVAL:
            bus_data = fetch_bus_data()  # returns tuple of lists
            last_bus_fetch = now_mono

        now = datetime.now()
        current_state = DisplayState.from_now(now, bus_data)

        if current_state != last_state:
            frame = render_frame(current_state, fonts)
            client.push_frame(frame)
            last_state = current_state

        time.sleep(1)
```

### Pattern 4: Configuration via Config Module

**What:** Quay IDs and other bus-specific settings are stored in `config.py` with environment variable overrides.

**When to use:** User decision requires stop/quay config to be configurable, not hardcoded.

**Example:**
```python
# In config.py
BUS_QUAY_DIRECTION1 = os.environ.get("BUS_QUAY_DIR1", "NSR:Quay:XXXXX")
BUS_QUAY_DIRECTION2 = os.environ.get("BUS_QUAY_DIR2", "NSR:Quay:YYYYY")
BUS_REFRESH_INTERVAL = 60  # seconds
BUS_NUM_DEPARTURES = 2
ET_CLIENT_NAME = os.environ.get("ET_CLIENT_NAME", "jdl-divoomhub")
```

### Anti-Patterns to Avoid

- **Fetching data inside the render function:** Network failures would freeze the display. The existing architecture explicitly separates data fetching from rendering (noted in Phase 1 research). Bus fetching must happen in the main loop, data flows through DisplayState to the renderer.
- **Querying StopPlace and filtering client-side:** Querying by quay ID is cleaner. The API does the direction filtering. Less data transferred, less parsing code.
- **Using async for a single synchronous loop:** The project has no async code. Adding `aiohttp`/`asyncio` for one HTTP call every 60 seconds adds complexity for zero benefit.
- **Hardcoding quay IDs in the provider:** Config module or environment variables per user decision.
- **Ignoring API errors and crashing:** A failed bus fetch must not crash the main loop. Catch exceptions, log them, keep the last known data or show empty state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO 8601 datetime parsing | Custom regex for timestamp strings | `datetime.fromisoformat()` (stdlib) | Handles timezone offsets, edge cases. Zero dependencies. |
| HTTP client | `urllib.request` with manual JSON encoding | `requests.post(url, json=...)` | Already installed. Cleaner API for POST with JSON body and headers. |
| GraphQL client framework | gql, graphql-core, or custom query builder | Raw query string + `requests.post()` | Single static query. No need for schema introspection or query validation. |
| Direction filtering | StopPlace query + regex on destination names | Entur quay-level queries | Quay IDs inherently filter by direction. Zero client-side logic needed. |
| Rate limiting | Custom token bucket or leaky bucket | Simple `time.monotonic()` timer | One request per 60 seconds needs no sophisticated rate limiter. |

**Key insight:** The Entur API does the heavy lifting (real-time tracking, direction filtering via quays, scheduled vs actual times). The provider is just a thin HTTP client that POSTs a static GraphQL query and parses 4 fields from the response.

## Common Pitfalls

### Pitfall 1: Timezone-Naive Datetime Comparison
**What goes wrong:** `datetime.now()` returns a naive datetime (no timezone). Entur's `expectedDepartureTime` is timezone-aware (ISO 8601 with offset, e.g., `2026-02-20T14:35:00+01:00`). Subtracting a naive datetime from an aware datetime raises `TypeError`.
**Why it happens:** Python's `datetime.now()` defaults to naive. Developers forget to make it timezone-aware.
**How to avoid:** Always use `datetime.now(tz=timezone.utc)` for the "now" reference, then subtract. Both datetimes will be timezone-aware and the subtraction works correctly regardless of local timezone.
**Warning signs:** `TypeError: can't subtract offset-naive and offset-aware datetimes`.

### Pitfall 2: Entur Rate Limiting (429 Too Many Requests)
**What goes wrong:** API returns HTTP 429, blocking further requests.
**Why it happens:** Entur enforces per-minute rate limits. The Home Assistant integration uses a 45-second minimum interval. Without the `ET-Client-Name` header, stricter limits are applied.
**How to avoid:** (1) Always send the `ET-Client-Name` header. (2) Enforce 60-second minimum between fetches. (3) Handle 429 gracefully -- log and retry on next cycle. Our 60-second refresh is well within limits.
**Warning signs:** HTTP 429 response status code. Missing `ET-Client-Name` header in requests.

### Pitfall 3: Quay IDs Not Known Upfront
**What goes wrong:** Developer uses the StopPlace ID (`NSR:StopPlace:42686`) but doesn't know the specific quay IDs for each direction.
**Why it happens:** Quay IDs are not obviously documented. They must be looked up.
**How to avoid:** Look up quay IDs before implementation using one of: (a) stoppested.entur.org web interface, (b) a one-time GraphQL query that lists all quays for the stop place, or (c) querying the stop place and inspecting which quay IDs appear in the response for each direction. This is noted as a blocker in STATE.md: "Phase 2 requires Ladeveien quay ID lookup (5-minute mechanical task via stoppested.entur.org)."
**Warning signs:** Using StopPlace query and getting mixed-direction results.

### Pitfall 4: Negative Countdown Values
**What goes wrong:** A bus that just departed shows as "-1 min" or a negative number.
**Why it happens:** Between the API fetch and the display render, a departure time can pass. Also, the `expectedDepartureTime` may be in the past if the bus is delayed and has already departed.
**How to avoid:** Clamp countdown to `max(0, minutes)`. A zero-minute countdown means "departing now." Negative values should be filtered out or clamped to 0.
**Warning signs:** Negative numbers appearing in the bus zone.

### Pitfall 5: Empty API Response (No Departures)
**What goes wrong:** Late at night or on holidays, no buses are running. The `estimatedCalls` array is empty.
**Why it happens:** No scheduled departures within the default time range.
**How to avoid:** Handle empty `estimatedCalls` gracefully. Show dashes or a "no buses" indicator. This is a Claude's Discretion item.
**Warning signs:** `IndexError` when accessing `estimatedCalls[0]` on an empty list.

### Pitfall 6: Network Timeout Crashing the Main Loop
**What goes wrong:** The Entur API is unreachable (network down, DNS failure, API outage), and the uncaught exception kills the entire dashboard.
**Why it happens:** `requests.post()` raises `ConnectionError`, `Timeout`, or other exceptions on network failure.
**How to avoid:** Wrap the API call in try/except. On failure, log the error and return the last known data (or None for empty state). The display continues showing the clock and last-known bus data.
**Warning signs:** Dashboard process exits unexpectedly. No bus data displayed but clock also stops.

### Pitfall 7: Bus Zone Text Overflow on 64px Width
**What goes wrong:** The bus line text (`>S  5  12`) exceeds 64 pixels horizontally.
**Why it happens:** With the 4x6 font, each character is 4-5px wide. The format `>S  5  12` is roughly 10-11 characters, which at 5px per char = 50-55px. This fits, but if countdown numbers are 3 digits (e.g., 120 minutes), or if wider fonts are used, overflow occurs.
**How to avoid:** Use the 4x6 ("tiny") font for bus data. Cap displayed minutes at a reasonable maximum (e.g., 99 or show "60+" for long waits). Test the widest possible string during implementation.
**Warning signs:** Text clipped at the right edge of the display.

## Code Examples

### Complete Entur GraphQL Query for a Quay

```python
# Source: Entur JourneyPlanner v3 API (verified via MMM-Entur-tavle, enturclient,
# No Rush project, BitBrb article, Home Assistant integration)
DEPARTURE_QUERY = """
{
  quay(id: "%s") {
    id
    name
    estimatedCalls(numberOfDepartures: %d, omitNonBoarding: true, timeRange: 3600) {
      expectedDepartureTime
      aimedDepartureTime
      realtime
      destinationDisplay {
        frontText
      }
      serviceJourney {
        line {
          publicCode
          transportMode
        }
      }
    }
  }
}
"""
# timeRange: 3600 = look ahead 1 hour (3600 seconds). Default is ~24 hours
# which returns too many results. 1 hour is sufficient for a departure board.
# omitNonBoarding: true = skip departures where passengers can't board
# (e.g., buses that only drop off at this stop).
```

### One-Time Quay ID Lookup Query

```python
# Run this ONCE during setup to find the quay IDs for Ladeveien.
# Execute via the Entur GraphQL IDE:
# https://api.entur.io/graphql-explorer/journey-planner-v3
QUAY_LOOKUP_QUERY = """
{
  stopPlace(id: "NSR:StopPlace:42686") {
    name
    id
    quays {
      id
      name
      publicCode
      estimatedCalls(numberOfDepartures: 1) {
        destinationDisplay {
          frontText
        }
      }
    }
  }
}
"""
# Response will list each quay with its ID and a sample departure showing
# the destination (frontText), which reveals the direction.
# Example output:
#   quay id: "NSR:Quay:XXXXX", frontText: "Sentrum"  -> direction 1
#   quay id: "NSR:Quay:YYYYY", frontText: "Lade"     -> direction 2
```

### ISO 8601 Countdown Calculation

```python
# Source: Python stdlib datetime docs (Python 3.14)
from datetime import datetime, timezone

def parse_countdown_minutes(iso_time_str: str) -> int:
    """Convert an ISO 8601 departure time to countdown minutes from now.

    Args:
        iso_time_str: ISO 8601 timestamp, e.g. "2026-02-20T14:35:00+01:00"

    Returns:
        Integer minutes until departure, minimum 0.
    """
    departure = datetime.fromisoformat(iso_time_str)
    now = datetime.now(tz=timezone.utc)
    delta = departure - now
    minutes = int(delta.total_seconds() / 60)
    return max(0, minutes)
```

### Bus Zone Rendering (within existing renderer pattern)

```python
# Source: Follows existing render_frame pattern from src/display/renderer.py
# Bus zone: y=24, height=19px. Two lines of text using tiny (4x6) font.
# Line 1: direction 1 (Sentrum) at y=25 (1px padding from top)
# Line 2: direction 2 (Lade) at y=34 (1px gap after 8px line height)

# With 4x6 font: each char ~5px wide including spacing
# ">S  5  12" = ~10 chars = ~50px. Fits in 64px with room to spare.

COLOR_BUS_DIR1 = (100, 200, 255)  # Light blue for Sentrum direction
COLOR_BUS_DIR2 = (255, 180, 50)   # Amber/orange for Lade direction
COLOR_BUS_TIME = (255, 255, 255)  # White for departure numbers

def render_bus_zone(draw, state, fonts):
    """Render bus departures in the bus zone."""
    if state.bus_direction1 is not None:
        # Direction 1 label
        draw.text((TEXT_X, 25), ">S", font=fonts["tiny"], fill=COLOR_BUS_DIR1)
        # Departure times
        times = "  ".join(str(m) for m in state.bus_direction1)
        draw.text((TEXT_X + 14, 25), times, font=fonts["tiny"], fill=COLOR_BUS_TIME)

    if state.bus_direction2 is not None:
        # Direction 2 label
        draw.text((TEXT_X, 34), "<L", font=fonts["tiny"], fill=COLOR_BUS_DIR2)
        # Departure times
        times = "  ".join(str(m) for m in state.bus_direction2)
        draw.text((TEXT_X + 14, 34), times, font=fonts["tiny"], fill=COLOR_BUS_TIME)
```

### Error-Resilient Fetch Wrapper

```python
# Source: Standard Python error handling pattern
import logging

logger = logging.getLogger(__name__)

def fetch_bus_data_safe(quay_id: str, num: int = 2) -> list[int] | None:
    """Fetch departures, returning None on any failure."""
    try:
        departures = fetch_departures(quay_id, num)
        return [d.minutes for d in departures]
    except Exception:
        logger.exception("Failed to fetch departures for %s", quay_id)
        return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Entur JourneyPlanner v2 | JourneyPlanner v3 (Transmodel-based) | v3 is current production endpoint | v2 IDE still referenced in old docs but v3 is the active endpoint at `api.entur.io/journey-planner/v3/graphql` |
| `enturclient` library (async, aiohttp) | Direct `requests` POST to GraphQL | Library last updated 2022 | For simple use cases, direct HTTP is simpler and avoids async complexity |
| `datetime.strptime()` for ISO 8601 | `datetime.fromisoformat()` | Python 3.11 (full ISO 8601 support) | Before 3.11, `fromisoformat` didn't handle all ISO formats. Now it does. |

**Deprecated/outdated:**
- **Entur JourneyPlanner v2:** Old IDE URL (`/v2/ide/`) still appears in some docs. Use v3 at `https://api.entur.io/journey-planner/v3/graphql`.
- **`enturclient` v0.2.4:** Last release July 2022. Works but adds unnecessary aiohttp dependency and async patterns.

## Open Questions

1. **Quay IDs for Ladeveien (NSR:StopPlace:42686)**
   - What we know: The stop place ID is `NSR:StopPlace:42686`. It has two directions: Sentrum and Lade.
   - What's unclear: The exact quay IDs (`NSR:Quay:XXXXX`) for each direction. These must be looked up.
   - Recommendation: Run the one-time quay lookup query (see Code Examples) via the Entur GraphQL IDE at `https://api.entur.io/graphql-explorer/journey-planner-v3` or programmatically during the first implementation task. This is a 5-minute mechanical task noted in STATE.md as a known prerequisite.

2. **Arrow Glyph Rendering in 4x6 BDF Font**
   - What we know: The user wants arrow glyphs (like `>` and `<` or triangle characters) next to the direction letter.
   - What's unclear: Whether the 4x6 BDF font includes filled triangle glyphs (e.g., U+25B6 `>` and U+25C0 `<`). These Unicode characters are outside Latin-1 (U+25xx range) and may not be present in the BDF fonts.
   - Recommendation: Test the BDF font for triangle/arrow glyphs. Fallback options: (a) use ASCII `>` and `<` which are guaranteed present, (b) draw a 3-4 pixel triangle using `ImageDraw.polygon()`, (c) use custom pixel art for the arrow glyph. The ASCII `>` / `<` approach is simplest and may look fine at 4x6 scale.

3. **Entur API Response Time Under Load**
   - What we know: The API is free and rate-limited. Home Assistant uses 45-second intervals.
   - What's unclear: Typical response latency. If the API takes >5 seconds, the main loop would block.
   - Recommendation: Set a 10-second timeout on the `requests.post()` call. If it times out, log and retry next cycle. The synchronous blocking is acceptable since the main loop only checks time every 1 second and bus data refreshes every 60 seconds -- a brief block once per minute is fine. If latency proves problematic during testing, moving the fetch to a background thread is a straightforward optimization.

## Sources

### Primary (HIGH confidence)
- [Entur JourneyPlanner v3 API](https://developer.entur.org/pages-journeyplanner-journeyplanner/) -- GraphQL endpoint at `https://api.entur.io/journey-planner/v3/graphql`. Open under NLOD license. Requires `ET-Client-Name` header.
- [Entur GraphQL IDE](https://api.entur.io/graphql-explorer/journey-planner-v3) -- Interactive query explorer for building and testing queries.
- [MMM-Entur-tavle (Arve)](https://github.com/Arve/MMM-Entur-tavle) -- MagicMirror module implementing Entur departure board. Confirmed GraphQL query structure, quay vs stop place distinction, `estimatedCalls` fields, `ET-Client-Name` header pattern.
- [enturclient (hfurubotten)](https://github.com/hfurubotten/enturclient) -- Python client for Entur. Confirmed API endpoint URL, GraphQL query fields (`expectedDepartureTime`, `aimedDepartureTime`, `realtime`, `destinationDisplay.frontText`, `serviceJourney.line.publicCode`), and response structure.
- [Python datetime docs](https://docs.python.org/3/library/datetime.html) -- `datetime.fromisoformat()` handles full ISO 8601 including timezone offsets (Python 3.11+). Confirmed for Python 3.14.
- [requests library](https://docs.python-requests.org/) -- `requests.post(url, json=..., headers=..., timeout=...)` for GraphQL POST requests. Already installed in project venv (v2.32.5).

### Secondary (MEDIUM confidence)
- [Home Assistant Entur integration](https://www.home-assistant.io/integrations/entur_public_transport/) -- Confirms 45-second minimum fetch interval for rate limiting. Uses both StopPlace and Quay ID formats. Warns about rate limiting consequences.
- [BitBrb GraphQL Bus Article](https://www.bitbrb.com/electronics/graphql-querying-a-bus) -- Confirmed quay-level query example (`quay(id: "NSR:Quay:7176")`), `estimatedCalls` response structure.
- [No Rush (Jonathan Rico)](https://jonathan.rico.live/projects/norush/) -- Confirmed API URL, `stopPlace` query pattern, `expectedDepartureTime` field, `destinationDisplay.frontText` for direction identification.
- [pidash wiki - Finding Quay IDs](https://github.com/ringvold/pidash/wiki/How-to-find-stop-and-quay-ids-for-the-Entur-API) -- Confirmed stoppested.entur.org for quay ID lookup, explained quay = specific platform/direction vs stop place = geographic area.

### Tertiary (LOW confidence)
- [Entur rate limiting docs](https://developer.entur.org/pages-customers-docs-ratelimiting/) -- Referenced but page content couldn't be fetched (JavaScript-rendered SPA). Rate limit details from Home Assistant issue tracker suggest per-minute quotas with 429 responses.
- [Entur authentication docs](https://developer.entur.org/pages-intro-authentication/) -- Referenced but page content couldn't be fetched. `ET-Client-Name` header format confirmed from multiple secondary sources as `"company-application"`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- `requests` already installed, `datetime.fromisoformat()` verified for Python 3.14, Entur API endpoint confirmed from 5+ independent sources.
- Architecture: HIGH -- Provider pattern established in Phase 1, extension to DisplayState is natural, independent refresh timer is straightforward.
- API integration: HIGH -- GraphQL query structure confirmed from multiple real-world implementations (MMM-Entur-tavle, enturclient, No Rush, Home Assistant). Endpoint URL, headers, and response format all cross-verified.
- Pitfalls: HIGH -- Timezone-naive comparison, rate limiting, empty responses, and network errors are well-documented across Entur community projects.
- Rendering: MEDIUM -- 4x6 font pixel math is sound but arrow glyph availability and exact spacing need hands-on testing.

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable domain; Entur API is production infrastructure, rarely changes)

---
*Phase: 02-bus-departures*
*Research completed: 2026-02-20*
