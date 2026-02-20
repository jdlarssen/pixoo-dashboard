---
phase: 02-bus-departures
plan: 02
subsystem: ui
tags: [pil, renderer, bus-zone, main-loop, pixoo]

# Dependency graph
requires:
  - phase: 02-bus-departures/01
    provides: "Bus provider (fetch_bus_data), DisplayState with bus fields, bus config constants"
  - phase: 01-foundation
    provides: "Renderer framework, layout zones, font loading, main loop, device push"
provides:
  - "Bus zone renderer drawing two direction lines with colored labels and countdown numbers"
  - "Main loop with independent 60-second bus fetch timer"
  - "Cancellation filtering -- cancelled departures excluded from display"
  - "3 departures per direction with correct arrow directions"
affects: [03-weather, 04-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [zone-renderer-helper, independent-refresh-timer, cancellation-filtering]

key-files:
  created: []
  modified:
    - src/display/renderer.py
    - src/display/layout.py
    - src/main.py
    - src/providers/bus.py
    - src/config.py
    - tests/test_renderer.py
    - tests/test_bus_provider.py

key-decisions:
  - "Arrow directions match actual travel: <S (Sentrum, leftward) and >L (Lade, rightward)"
  - "3 departures per direction for better planning visibility"
  - "Cancelled departures filtered silently -- request extra from API to compensate"
  - "Bus zone uses 5x8 font for countdown numbers (better readability than 4x6)"

patterns-established:
  - "Zone renderer helper: render_X_zone() called from render_frame()"
  - "Independent refresh timer: monotonic clock comparison for non-blocking periodic fetch"
  - "Cancellation filtering: request N+3 from API, skip cancelled, return first N"

requirements-completed: [BUS-01, BUS-02, BUS-03, BUS-05]

# Metrics
duration: 12min
completed: 2026-02-20
---

# Phase 2 Plan 2: Bus Zone Renderer Summary

**Live bus departures rendered in 19px zone with colored direction labels, 3 countdown numbers per line, cancelled buses filtered, verified on physical Pixoo 64**

## Performance

- **Duration:** 12 min (including checkpoint verification on physical device)
- **Started:** 2026-02-20T19:01:00Z
- **Completed:** 2026-02-20T19:13:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Bus zone renders two direction lines: light blue `<S` (Sentrum) and amber `>L` (Lade) with white countdown numbers
- Main loop fetches bus data every 60 seconds via independent monotonic timer
- Cancelled departures filtered out at provider level (API query includes `cancellation` field)
- 3 departures shown per direction instead of 2
- Verified working on physical Pixoo 64 -- readable from distance with clear color distinction
- 53 tests passing (11 new: 8 renderer + 3 cancellation filtering)

## Task Commits

Each task was committed atomically:

1. **Task 1: Bus zone renderer and main loop integration** - `10eafa5` (feat)
2. **Task 2: Checkpoint feedback (arrows, 3 departures, cancellation)** - `21580f0` (feat)

## Files Created/Modified
- `src/display/layout.py` - Added COLOR_BUS_DIR1 (light blue), COLOR_BUS_DIR2 (amber), COLOR_BUS_TIME (white)
- `src/display/renderer.py` - render_bus_zone() helper with _draw_bus_line(), imports BUS_NUM_DEPARTURES
- `src/main.py` - Independent 60-second bus fetch timer using time.monotonic()
- `src/providers/bus.py` - Added `cancellation` to GraphQL query, skip cancelled departures, request extra to compensate
- `src/config.py` - BUS_NUM_DEPARTURES changed from 2 to 3
- `tests/test_renderer.py` - 8 bus zone rendering tests (data, None, partial, zero, empty, long waits)
- `tests/test_bus_provider.py` - 3 cancellation filtering tests added

## Decisions Made
- Arrow directions corrected per user feedback: `<S` (Sentrum is leftward from Ladeveien), `>L` (Lade is rightward)
- Show 3 departures per direction (user request -- more useful for planning)
- Cancelled departures silently filtered: request `num_departures + 3` from API, skip cancelled entries, return first N
- Dashes `-- --` shown for missing data (dim gray) -- clear "no data" indication
- 5x8 font for countdown numbers provides better readability than 4x6

## Deviations from Plan

### Auto-fixed Issues

**1. Checkpoint feedback: arrow directions and departure count**
- **Found during:** Task 2 (Physical device verification)
- **Issue:** User corrected arrow directions (`<S` not `>S`, `>L` not `<L`) and requested 3 departures per direction
- **Fix:** Swapped arrows in renderer, changed BUS_NUM_DEPARTURES to 3
- **Files modified:** src/display/renderer.py, src/config.py
- **Verification:** Confirmed on physical device
- **Committed in:** `21580f0`

**2. Checkpoint feedback: cancelled bus filtering**
- **Found during:** Task 2 (Physical device verification)
- **Issue:** User noticed a cancelled bus showing in the Entur data -- no point displaying it
- **Fix:** Added `cancellation` field to GraphQL query, filter cancelled departures in provider
- **Files modified:** src/providers/bus.py, tests/test_bus_provider.py
- **Verification:** 3 new cancellation tests pass, live API query confirms field available
- **Committed in:** `21580f0`

---

**Total deviations:** 2 checkpoint-driven (user feedback on physical device)
**Impact on plan:** Better UX -- correct direction indicators, more departure info, no phantom cancelled buses.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bus departure display complete and verified on physical hardware
- Weather zone placeholder ready for Phase 3 implementation
- Main loop pattern established for adding additional periodic data fetches
- All 53 tests pass

## Self-Check: PASSED

All files exist, all commits verified, physical device verification passed.

---
*Phase: 02-bus-departures*
*Completed: 2026-02-20*
