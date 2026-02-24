---
phase: 10-radial-ray-system
plan: 01
subsystem: display
tags: [pillow, pil, led-animation, weather-zone, polar-coordinates, sun-rays]

# Dependency graph
requires:
  - phase: 09-sun-body
    provides: "Corner-anchored quarter-sun body at (63,0) r=8 with _SUN_X/_SUN_Y constants"
provides:
  - "Polar radial ray system emitting from sun body in 95-160 degree fan"
  - "Distance-based alpha fade for natural light-emission effect"
  - "Continuous respawn at origin with re-randomized parameters"
  - "TestRadialRays with 4 tests validating ray clustering, state, respawn, stagger"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Polar ray state [angle, distance, speed, max_dist, base_alpha] for radial emission"
    - "Distance-based alpha fade: base_alpha * (1 - distance/max_dist)"
    - "Re-randomize ray parameters on respawn to prevent synchronization"
    - "Draw sun body after rays to prevent pixel overwrite on shared bg layer"

key-files:
  created: []
  modified:
    - src/display/weather_anim.py
    - tests/test_weather_anim.py

key-decisions:
  - "95-160 degree fan range for downward-facing rays from top-right corner"
  - "Far rays speed 0.3-0.6, near rays 0.5-1.0 for parallax depth effect"
  - "Draw sun body after far rays to prevent PIL overwrite of body pixels"
  - "Re-randomize all ray parameters on respawn for organic variety"

patterns-established:
  - "Polar particle state for radial emission from a fixed origin"
  - "LED visibility threshold alpha < 15 cutoff for distance fade"

requirements-completed: [ANIM-03, ANIM-04, ANIM-05, ANIM-06, ANIM-07, TEST-02]

# Metrics
duration: 3min
completed: 2026-02-23
---

# Phase 10 Plan 1: Radial Ray System Summary

**Polar radial rays emitting in 95-160 degree fan from corner sun with distance-based alpha fade, staggered spawn, and re-randomized respawn**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-23T21:57:59Z
- **Completed:** 2026-02-23T22:00:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced cartesian random-scatter rays with polar radial system emitting from sun body at (63, 0)
- Rays fade naturally with distance using `base_alpha * (1 - distance/max_dist)` formula
- Continuous respawn at origin with re-randomized angle, speed, max_dist, base_alpha prevents synchronization
- Staggered initial distances ensure animation starts mid-flow without burst effect
- 4 new regression tests validating clustering, polar state, respawn, and stagger behavior
- All 75 tests pass (71 existing + 4 new) with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite SunAnimation rays from cartesian to polar radial system** - `ad18bc0` (feat)
2. **Task 2: Add ray origin clustering test (TEST-02)** - `38c44ab` (test)

**Auto-fix:** `2f48e04` (fix: draw sun body after far rays to prevent pixel overwrite)

## Files Created/Modified
- `src/display/weather_anim.py` - SunAnimation rewritten: polar ray state, fan constants, distance fade, respawn logic, draw order fix
- `tests/test_weather_anim.py` - Added TestRadialRays class with 4 tests: clustering, polar state, respawn, stagger

## Decisions Made
- 95-160 degree fan range chosen to cover the visible 64x24 zone diagonally from the top-right corner
- Far ray speed 0.3-0.6 px/tick, near ray speed 0.5-1.0 px/tick maintains ~1.5-2x parallax ratio
- Re-randomize all ray parameters on respawn (not just distance) to prevent periodic synchronization
- Sun body drawn after far rays on bg layer to prevent PIL ImageDraw overwrite of body pixels

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sun body pixel overwrite by ray segments**
- **Found during:** Verification after Task 2
- **Issue:** PIL ImageDraw.line() overwrites (not composites) pixels. Far rays near the sun origin could overwrite sun body pixels, reducing alpha from 200 to ray alpha (~92). This caused intermittent TestSunBody::test_sun_body_produces_warm_pixels_at_position failure.
- **Fix:** Moved `_draw_sun_body()` call to after far ray drawing in `tick()`, so body pixels always dominate.
- **Files modified:** src/display/weather_anim.py
- **Verification:** 5 consecutive test runs, all 75 tests passing each time.
- **Committed in:** 2f48e04

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for draw-order correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed draw order issue.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 10 complete. This was the final phase of v1.2 Sun Ray Overhaul milestone.
- All v1.2 requirements met: sun body (Phase 9) + radial rays (Phase 10)
- Milestone ready for completion.

## Self-Check: PASSED

- All files exist (SUMMARY.md, weather_anim.py, test_weather_anim.py)
- All commits found (ad18bc0, 38c44ab, 2f48e04)
- 75/75 tests passing consistently

---
*Phase: 10-radial-ray-system*
*Completed: 2026-02-23*
