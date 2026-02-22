---
status: resolved
trigger: "Weather animations are too subtle/dim on the Pixoo 64 LED display, and the star (clear night) animation lacks randomness"
created: 2026-02-22T00:00:00Z
updated: 2026-02-22T00:00:00Z
---

## Current Focus

hypothesis: Confirmed — alpha values too conservative + star twinkle uses uniform sinusoidal pattern
test: All 141 tests pass including 6 new star randomness regression tests
expecting: Animations visibly brighter on LED hardware; stars twinkle organically
next_action: Archive session

## Symptoms

expected:
1. Weather animations should be clearly visible on the LED display
2. ClearNightAnimation stars should feel organic — varied blink durations/intervals per star

actual:
1. Animations are too subtle/dim — barely visible on hardware
2. Stars blink in uniform sinusoidal pattern — all use same phase/frequency, looks mechanical

errors: No errors — visual quality/feel issue
reproduction: Run dashboard at night with clear sky for stars, any weather for other animations
started: Animations have always been too subtle

## Eliminated

- hypothesis: Prior session already eliminated other possibilities
  evidence: Detailed root cause analysis in .planning/debug/weather-animation-too-subtle.md
  timestamp: 2026-02-20

## Evidence

- timestamp: 2026-02-22
  checked: renderer.py _composite_layer function (lines 122-126)
  found: FIXED — renderer now uses proper alpha compositing (crop region as RGBA, alpha_composite, paste RGB). The old double-alpha bug from the prior session has been fixed.
  implication: Root cause #1 (double alpha) was already addressed.

- timestamp: 2026-02-22
  checked: pixoo_client.py push_frame (line 63)
  found: Rate limit is now 0.3s (was 1.0s in prior session). main.py sleep is 0.35s.
  implication: Root cause #2 (rate limiter) was already addressed.

- timestamp: 2026-02-22
  checked: weather_anim.py alpha values (pre-fix)
  found: Alpha values partially improved from prior but still too conservative for LED hardware (rain far=100, snow far=90, cloud far=60/45, sun far=70-110, fog far=40-65).
  implication: Far/background particles still too dim on LED matrix.

- timestamp: 2026-02-22
  checked: weather_anim.py particle sizes (pre-fix)
  found: Snow far flakes still single pixel. Rain improved to streaks.
  implication: Snow far flakes invisible at lower alpha values.

- timestamp: 2026-02-22
  checked: ClearNightAnimation twinkle mechanism (pre-fix)
  found: All stars use `math.sin(phase)` with speed range 0.08-0.25. Uniform sinusoidal oscillation — no variation in on/off duration, no dark intervals, all stars always visible.
  implication: Mechanical/uniform pattern, not organic.

- timestamp: 2026-02-22
  checked: Post-fix verification — full test suite
  found: 141/141 tests pass including 6 new star randomness tests
  implication: Fix is correct and complete, no regressions.

## Resolution

root_cause: |
  1. Alpha values too conservative for LED hardware visibility (far particles especially)
  2. Snow far flakes single pixel — invisible at lower alpha
  3. Star animation uses uniform sinusoidal oscillation — all stars twinkle at similar frequency with no dark intervals, producing mechanical pattern

fix: |
  A. Boosted alpha values across ALL animations:
     - Rain: far 100->140, near 200->230
     - Snow: far 90->130 (+ second pixel at 100), near 180->210
     - Cloud: far 60/45->90/70, near 90/70->130/100
     - Sun: far 70-110->100-140, near 130-180->160-220
     - Fog: far 40-65->65-90, near 70-110->100-140
  B. Snow far flakes: 1px -> 2px horizontal pair (primary + dimmer secondary pixel)
  C. ClearNightAnimation completely redesigned with state machine:
     - 4 states per star: DARK -> BRIGHTEN -> PEAK -> DIM -> DARK
     - Each star has independently randomized durations for each phase
     - Dark intervals: far stars 6-30 ticks, near stars 4-20 ticks
     - Brighten/dim ramps: varied per star (2-12 ticks)
     - Peak hold: varied per star (2-10 ticks)
     - Peak alpha: far 80-150, near 160-240
     - All durations RE-RANDOMIZED after each full cycle (every blink is unique)
     - Stars start at random points in their cycle (no sync)
     - Increased star count: far 12->14, near 5->6
  D. Removed unused `import math` (sinusoidal twinkle removed)
  E. Updated test thresholds to enforce new higher alpha minimums
  F. Added 6 new regression tests for star randomness

verification: |
  - 141/141 tests pass (0 failures, 0 regressions)
  - New TestStarRandomness tests verify:
    - Stars have varied peak alphas (>= 5 distinct values across 20 stars)
    - Stars have varied dark durations (>= 4 distinct values)
    - Stars start in different states (not synchronized)
    - Some stars are dark at any given tick (organic on/off pattern)
    - Individual star alpha varies over time (state machine transitioning)
    - Durations re-randomize after each cycle (every blink unique)
  - Alpha threshold tests tightened to prevent regression to lower values

files_changed:
  - src/display/weather_anim.py
  - tests/test_weather_anim.py
