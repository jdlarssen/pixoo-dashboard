---
status: resolved
trigger: "moon icon in clock zone looks like heart/blob instead of crescent moon"
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - ellipse-based crescent produces a diagonal slash/zigzag pattern, not a recognizable crescent. The cutout circle removes too much, leaving only a 3px-wide diagonal stripe.
test: Rendered _draw_moon(10) and inspected pixel grid
expecting: N/A - root cause confirmed
next_action: Replace with hand-crafted pixel bitmap crescent moon

## Symptoms

expected: Recognizable crescent moon shape at 10x10 pixel resolution
actual: Icon renders as heart/blob on real 64x64 LED display. User described it as "a comma laying rotated 90 degrees" initially, and "a heart/blob" after first fix attempt
errors: No errors - purely visual quality issue
reproduction: Run dashboard at night; moon icon appears next to time in clock zone
started: Moon icon has never looked right. Two fix attempts using circle/ellipse math both failed.

## Eliminated

## Evidence

- timestamp: 2026-02-21T00:01:00Z
  checked: Rendered _draw_moon(10) pixel grid
  found: |
    The current output is a diagonal zigzag stripe, 3 pixels wide, running from top-right to bottom-left and back:
    . . . . . . . . . .
    . . . . . # # # . .
    . . . # # # . . . .
    . . . # # # . . . .
    . . # # # . . . . .
    . . # # # . . . . .
    . . # # # . . . . .
    . . . # # # . . . .
    . . . # # # . . . .
    . . . . . # # # . .
    This does NOT read as a crescent moon. It's a wobbly diagonal band.
  implication: The ellipse subtraction approach fundamentally cannot produce a good crescent at 10px. The two r=4 circles with +3 offset leave only a thin diagonal stripe. Need hand-crafted pixel bitmap instead.

- timestamp: 2026-02-21T00:01:30Z
  checked: Color used by current moon
  found: Color is rgba(220,225,235,255) - silver-blue. Layout.py has COLOR_WEATHER_TEMP=(255,220,50) as warm yellow. A warmer moon color like golden yellow would be more recognizable.
  implication: Color could also be improved to warm yellow/gold for better LED visibility

## Resolution

root_cause: Pillow's draw.ellipse() with circle subtraction produces a 3px-wide diagonal zigzag stripe at 10px resolution, not a recognizable crescent. Mathematical approaches to tiny pixel art produce rasterization artifacts. Need hand-crafted bitmap.
fix: Replace ellipse-based _draw_moon() with hand-crafted 10x10 pixel bitmap using pre-defined coordinates. Use warm golden yellow color (255, 220, 100) instead of cold silver-blue.
verification: |
  1. New _draw_moon(10) renders clean 10x10 crescent (34 lit pixels, correct shape)
  2. get_weather_icon("clearsky_night") returns correct crescent via full API path
  3. Sun icon (clearsky_day) still works (33 lit pixels)
  4. Partcloud night still works (42 lit pixels)
  5. All 112 tests pass with zero failures
  6. No import changes needed (ImageDraw still used by other functions)
files_changed: [src/display/weather_icons.py]
