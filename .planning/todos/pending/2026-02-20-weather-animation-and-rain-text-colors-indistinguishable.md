---
created: 2026-02-20T20:26:53.825Z
title: Weather animation and rain text colors indistinguishable
area: display
files:
  - src/display/weather_anim.py
  - src/display/renderer.py
---

## Problem

After the animation visibility gap closure (plan 03-03), weather animations are now visible but the particle color (rain/snow) is grey, which is the same color as the rain indicator text ("1/1"). This makes it hard to:

1. Distinguish rain from snow — both appear as grey particles
2. Distinguish animation particles from the rain indicator text — both are grey
3. Identify what weather condition is being shown at a glance

User reported: "The raindrops, or is it snow? I don't know, they are grey. So are the letters for 1/1."

## Solution

- Rain particles should be blue-tinted (e.g., light blue RGB) to clearly read as water
- Snow particles should be white/bright to read as snow
- Rain indicator text ("1/1") should use a distinct color from animation particles (e.g., cyan or white)
- Each animation type should have a visually distinct color palette so the weather condition is immediately recognizable
- Investigate current fill colors in `weather_anim.py` animation classes and `renderer.py` text rendering
