---
phase: 04-polish-and-reliability
plan: 01
subsystem: display
tags: [pil, rendering, bus, error-handling, staleness]

requires:
  - phase: 02-bus-departures
    provides: Bus zone renderer with _draw_bus_line
  - phase: 03-weather
    provides: Weather zone renderer and animation overlay
provides:
  - Per-departure urgency color rendering (green/yellow/red/dimmed thresholds)
  - urgency_color() helper function in layout.py
  - Staleness tracking with last-good data preservation in main loop
  - Visual staleness indicator (orange dot) for bus and weather zones
  - Graceful degradation to dash placeholders when data is too old
affects: [04-polish-and-reliability]

tech-stack:
  added: []
  patterns:
    - "Urgency color function: urgency_color(minutes) returns RGB tuple based on thresholds"
    - "Last-good data: preserve previous successful fetch result when API returns None"
    - "Staleness flags: boolean fields on DisplayState driven by monotonic timestamp age"

key-files:
  created: []
  modified:
    - src/display/layout.py
    - src/display/renderer.py
    - src/display/state.py
    - src/main.py

key-decisions:
  - "Per-departure rendering: each countdown number drawn individually with cursor tracking for correct spacing"
  - "Staleness thresholds: bus stale 180s / too_old 600s, weather stale 1800s / too_old 3600s"
  - "Orange 1px dot at top-right of zone for staleness indicator -- subtle but visible"
  - "too_old passes None to DisplayState to show dash placeholders via existing placeholder logic"

patterns-established:
  - "Urgency color: layout.py urgency_color(minutes) -> RGB, used by renderer per-departure"
  - "Last-good preservation: main loop tracks last_good_{source} and last_good_{source}_time"
  - "Staleness calculation: age = now_mono - last_good_time, flags set by threshold comparison"

requirements-completed: [BUS-04, RLBL-02]

duration: 8min
completed: 2026-02-20
---

# Phase 4: Polish and Reliability - Plan 01 Summary

**Per-departure urgency colors for bus countdowns with last-good data preservation and staleness indicators**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20
- **Completed:** 2026-02-20
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Bus departure numbers render in urgency colors: green (>10 min), yellow (5-10), red (<5), dimmed (<2)
- API failures preserved last-good data instead of blanking display
- Orange staleness indicator dot appears when data is aging
- Dash placeholders shown when data exceeds age threshold

## Task Commits

Each task was committed atomically:

1. **Task 1: Add urgency color system for bus departures** - `f462e89` (feat)
2. **Task 2: Add staleness tracking and graceful error states** - `ec28116` (feat)

## Files Created/Modified
- `src/display/layout.py` - Urgency color constants, urgency_color() helper, staleness indicator color
- `src/display/renderer.py` - Per-departure urgency color rendering, staleness dot indicators
- `src/display/state.py` - Staleness fields (bus_stale, bus_too_old, weather_stale, weather_too_old)
- `src/main.py` - Last-good data preservation, staleness age tracking, threshold calculations

## Decisions Made
- Each departure number drawn individually with cursor tracking (not a single string) to support per-number coloring
- Staleness thresholds based on data type: bus 3min/10min, weather 30min/1hr
- 1px orange dot as staleness indicator -- subtle but visible on LED

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Urgency colors and staleness tracking ready for visual overhaul in plan 04-02
- Layout constants ready for zone rebalancing

---
*Phase: 04-polish-and-reliability*
*Completed: 2026-02-20*
