---
phase: 03-weather
plan: 03
subsystem: display
tags: [pillow, alpha-compositing, led-display, animation, pixoo]

# Dependency graph
requires:
  - phase: 03-weather/02
    provides: "Weather zone renderer, animation framework, weather icons"
provides:
  - "LED-visible weather animations with single-pass alpha compositing"
  - "Rate limiter tuned for ~3 FPS animation (0.3s minimum interval)"
  - "Animation alpha/size regression tests preventing future dimming"
affects: [04-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: ["single-pass alpha compositing for LED overlays", "animation visibility regression testing"]

key-files:
  created:
    - tests/test_weather_anim.py
  modified:
    - src/display/renderer.py
    - src/device/pixoo_client.py
    - src/main.py
    - src/display/weather_anim.py

key-decisions:
  - "Single-pass alpha_composite replaces double-alpha paste+mask pattern"
  - "Rate limiter 0.3s (was 1.0s) with 0.35s sleep to prevent jitter drops"
  - "Animation alphas in 65-150 range based on LED matrix visibility threshold"

patterns-established:
  - "LED visibility gate: all animation alpha values must stay above 50 per test enforcement"
  - "Rate limiter alignment: animation sleep must exceed rate limit minimum to avoid silent frame drops"

requirements-completed: []

# Metrics
duration: 4min
completed: 2026-02-20
---

# Phase 3 Plan 3: Weather Animation Visibility Summary

**Single-pass alpha compositing, tuned rate limiter (0.3s), and LED-visible animation alphas (65-150) fixing invisible weather backgrounds on Pixoo 64**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-20T20:14:00Z
- **Completed:** 2026-02-20T20:18:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Fixed triple-compounding invisibility bug: double alpha compositing + overly conservative rate limiter + too-dim alpha values
- Weather zone animations now produce LED-visible pixel values (RGB > 20 per channel, verified by pixel sanity check)
- New test file enforces minimum alpha and particle coverage thresholds as a regression gate
- All 92 tests pass (82 original + 10 new animation visibility tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix compositing, rate limiter, and animation loop alignment** - `33ec107` (fix)
2. **Task 2: Increase animation alpha values and particle sizes for LED visibility** - `97378e6` (feat)

## Files Created/Modified
- `src/display/renderer.py` - Single-pass alpha_composite replacing double-alpha paste+mask
- `src/device/pixoo_client.py` - Rate limiter minimum interval lowered from 1.0s to 0.3s
- `src/main.py` - Animation sleep aligned to 0.35s (slightly above rate limit)
- `src/display/weather_anim.py` - All alpha values raised to 65-150 range, multi-pixel particles, halved movement speeds
- `tests/test_weather_anim.py` - 10 tests enforcing alpha minimums and pixel coverage thresholds

## Decisions Made
- Single-pass alpha_composite replaces the double-alpha paste+mask pattern that was squashing effective opacity from ~20% to ~4%
- Rate limiter lowered from 1.0s to 0.3s (Pixoo 64 handles ~3 FPS over HTTP without lockup)
- Animation loop sleep set to 0.35s (not 0.3s) to provide jitter margin and prevent silent frame drops
- Rain particles changed from 1px points to 1x2 vertical streaks for LED visibility
- Snow particles changed from 1px points to 2x1 horizontal rectangles for LED visibility
- Movement speeds halved across all animations to maintain similar visual speed at ~3x the effective frame rate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Snow multi-pixel test threshold too tight for edge clipping**
- **Found during:** Task 2 (animation parameter tuning)
- **Issue:** Snow test threshold of 28 pixels assumed all 15 flakes produce 2 pixels each, but flakes at x=63 get edge-clipped to 1 pixel, and random overlaps reduce count
- **Fix:** Lowered threshold from 28 to 20 (still well above 15 which would indicate single-pixel particles)
- **Files modified:** tests/test_weather_anim.py
- **Verification:** Test passes consistently across multiple runs
- **Committed in:** 97378e6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test threshold adjustment for edge-case correctness. No scope creep.

## Issues Encountered
None -- both tasks executed cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Weather animation visibility gap closed -- all three root causes addressed
- Ready for Phase 4 (polish) or UAT retest of weather animation
- 92 tests passing as regression gate

## Self-Check: PASSED

All 6 files verified present. Both task commits (33ec107, 97378e6) confirmed in git log. 92 tests passing.

---
*Phase: 03-weather*
*Completed: 2026-02-20*
