---
created: 2026-02-22T20:09:28.325Z
title: Rain animation intensity should reflect precipitation amount
area: display
files:
  - src/display/weather_anim.py
  - src/display/state.py
  - src/display/renderer.py
---

## Problem

The rain animation always plays at the same intensity regardless of how much precipitation the API reports. If it's pouring outside (e.g. 5mm/h), the animation should show heavy, dense rain. If it's just light drizzle (e.g. 0.2mm/h), it should be sparse and gentle.

The `precipitation_mm` value is already available in `WeatherData` and `DisplayState` — it just isn't passed to the animation system.

## Solution

TBD - needs investigation. Likely approach: pass `precipitation_mm` to `RainAnimation` and scale particle count, speed, and/or alpha based on the value. Could use thresholds (light < 1mm, moderate 1-3mm, heavy > 3mm) or continuous scaling.
