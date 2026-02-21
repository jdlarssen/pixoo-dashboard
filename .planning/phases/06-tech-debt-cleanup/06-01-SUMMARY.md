---
phase: 06-tech-debt-cleanup
plan: 01
subsystem: infra
tags: [pillow, deprecation, dead-code, config, cleanup]

# Dependency graph
requires:
  - phase: 05-verification-and-cleanup
    provides: "v1.0 milestone audit identifying dead code and deprecation issues"
provides:
  - "Clean config.py with only active constants (FONT_LARGE and PUSH_INTERVAL removed)"
  - "Accurate main_loop() docstring reflecting current font keys"
  - "Deprecation-free test suite using Pillow get_flattened_data()"
  - "Pillow>=12.1.0 version floor in pyproject.toml"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["get_flattened_data() replaces deprecated getdata() for Pillow pixel access"]

key-files:
  created: []
  modified:
    - src/config.py
    - src/main.py
    - tests/test_weather_anim.py
    - tests/test_fonts.py
    - pyproject.toml

key-decisions:
  - "PUSH_INTERVAL also removed (dead -- main loop uses hardcoded sleep values, never imported)"
  - "get_flattened_data() is a drop-in replacement for getdata() -- both return iterables of tuples"
  - "Pillow>=12.1.0 floor prevents breakage if environment recreated with older Pillow"

patterns-established:
  - "Use get_flattened_data() instead of getdata() for all Pillow pixel data access"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 6 Plan 1: Dead Code & Deprecation Cleanup Summary

**Removed dead constants FONT_LARGE and PUSH_INTERVAL, fixed stale docstring, replaced 3 deprecated Pillow getdata() calls, pinned Pillow>=12.1.0**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21
- **Completed:** 2026-02-21
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Removed FONT_LARGE and PUSH_INTERVAL dead constants from config.py (zero imports outside config.py confirmed by grep)
- Fixed main_loop() docstring to reference only "small", "tiny" font keys (not the removed "large")
- Replaced all 3 deprecated Pillow getdata() calls with get_flattened_data() in test files
- Pinned Pillow>=12.1.0 version floor in pyproject.toml
- Full test suite passes: 96/96 tests, zero deprecation warnings

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead constants and fix stale docstring** - `14753c1` (fix)
2. **Task 2: Replace deprecated getdata() and pin Pillow version** - `4c4a6d9` (fix)

## Files Created/Modified
- `src/config.py` - Removed FONT_LARGE and PUSH_INTERVAL (2 dead constants)
- `src/main.py` - Fixed main_loop() docstring (removed "large" from font keys)
- `tests/test_weather_anim.py` - Replaced 2 getdata() calls with get_flattened_data()
- `tests/test_fonts.py` - Replaced 1 getdata() call with get_flattened_data()
- `pyproject.toml` - Changed "Pillow" to "Pillow>=12.1.0"

## Decisions Made
- PUSH_INTERVAL was also identified as dead (defined but never imported anywhere) -- removed alongside FONT_LARGE
- get_flattened_data() confirmed as exact drop-in: both return iterables of tuples, all call sites use iteration (max, sum, list)
- Version floor pin is conservative (>=12.1.0, not <14) per research recommendation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- config.py is clean -- only active constants remain
- Test suite is deprecation-warning-free
- Ready for plan 06-02 (SUMMARY frontmatter)

## Self-Check: PASSED

All files verified. Both commits confirmed (14753c1, 4c4a6d9). 96 tests pass.

---
*Phase: 06-tech-debt-cleanup*
*Completed: 2026-02-21*
