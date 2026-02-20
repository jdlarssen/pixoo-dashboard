---
phase: 02-bus-departures
plan: 01
subsystem: api
tags: [entur, graphql, bus-departures, requests, dataclass]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "DisplayState with dirty flag pattern, config module with env var pattern"
provides:
  - "Bus departure provider (fetch_departures, fetch_departures_safe, fetch_bus_data)"
  - "BusDeparture dataclass with countdown minutes"
  - "DisplayState extended with bus_direction1/bus_direction2 tuple fields"
  - "Bus config constants (quay IDs, refresh interval, API URL, client name)"
affects: [02-bus-departures, 03-weather, 04-polish]

# Tech tracking
tech-stack:
  added: [requests (existing, now used for Entur API)]
  patterns: [provider-with-safe-wrapper, graphql-via-raw-post, countdown-from-iso8601]

key-files:
  created:
    - src/providers/bus.py
    - tests/test_bus_provider.py
  modified:
    - src/config.py
    - src/display/state.py

key-decisions:
  - "Quay ID lookup from Entur API: NSR:Quay:73154 (Sentrum) and NSR:Quay:73152 (Lade/Strindheim)"
  - "DisplayState bus fields use tuples (not lists) to preserve hashability for dirty flag pattern"
  - "fetch_departures_safe returns list[int] | None -- simplified for renderer consumption"

patterns-established:
  - "Provider safe wrapper: fetch_X_safe() catches all exceptions, logs, returns None"
  - "GraphQL via raw requests.post -- no framework needed for static queries"
  - "Countdown math: datetime.fromisoformat() + timezone-aware subtraction + clamp to 0"

requirements-completed: [BUS-01, BUS-02, BUS-03, BUS-05]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 2 Plan 1: Bus Data Provider Summary

**Entur JourneyPlanner v3 GraphQL client fetching real-time bus departures for two Ladeveien quays with countdown minutes and error-safe wrappers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T18:55:16Z
- **Completed:** 2026-02-20T18:58:07Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Looked up real quay IDs from Entur API: NSR:Quay:73154 (Sentrum direction) and NSR:Quay:73152 (Lade/Strindheim direction)
- Bus provider fetches real-time departures, calculates countdown minutes from ISO 8601 timestamps, clamps negatives to 0
- Error-safe wrapper ensures API failures never crash the main loop (returns None)
- DisplayState extended with bus_direction1/bus_direction2 as optional tuples preserving dirty flag equality
- 14 new tests covering countdown math, negative clamping, response parsing, error handling, and DisplayState equality

## Task Commits

Each task was committed atomically:

1. **Task 1: Quay ID lookup and bus configuration** - `a2dfe0b` (feat)
2. **Task 2: Bus departure provider and DisplayState extension** - `d97bb12` (feat)

## Files Created/Modified
- `src/config.py` - Added bus configuration: quay IDs, refresh interval, API URL, client name (all env-var configurable)
- `src/providers/bus.py` - Entur GraphQL client with BusDeparture dataclass, fetch_departures, fetch_departures_safe, fetch_bus_data
- `src/display/state.py` - Extended DisplayState with bus_direction1/bus_direction2 tuple fields and updated from_now()
- `tests/test_bus_provider.py` - 14 tests for countdown calculation, response parsing, error handling, DisplayState bus fields

## Decisions Made
- Quay IDs discovered from live Entur API: NSR:Quay:73154 serves Sentrum direction ("Lund via Lade-sentrum-Kolstad"), NSR:Quay:73152 serves Lade direction ("Strindheim via Lade")
- Bus fields in DisplayState use tuples (not lists) so dataclass equality comparison works for the dirty flag pattern
- fetch_departures_safe() returns `list[int] | None` (just minutes) rather than full BusDeparture objects -- the renderer only needs countdown numbers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The Entur API is free and requires no authentication.

## Next Phase Readiness
- Bus data provider ready for Plan 02 (bus zone renderer) to consume via fetch_bus_data()
- DisplayState carries bus data through the dirty flag pattern
- Live API confirmed working: returns real departure data for both directions
- All 42 tests pass (14 new + 28 existing)

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 02-bus-departures*
*Completed: 2026-02-20*
