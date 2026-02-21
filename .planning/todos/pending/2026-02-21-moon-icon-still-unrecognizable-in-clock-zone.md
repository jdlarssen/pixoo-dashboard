---
created: 2026-02-21T20:23:53.371Z
title: Moon icon still unrecognizable in clock zone
area: display
files:
  - src/display/weather_icons.py
---

## Problem

The moon icon shown next to the time in the clock zone (top-right) still looks like a heart or blob shape instead of a recognizable crescent moon. A previous fix (commit 21bd119) improved `_draw_moon()` from r=3 to r=4 with a better crescent cut-out, but it's still not right on the actual 64x64 LED hardware.

Screenshot from the physical display confirms the icon renders as an unrecognizable shape at 10x10 pixel size.

## Solution

TBD - needs investigation of the actual pixel art in `_draw_moon()`. May need to hand-craft a simple crescent shape pixel-by-pixel rather than using circle/ellipse math, since the resolution is so low (10x10 px) that geometric approaches produce artifacts.
