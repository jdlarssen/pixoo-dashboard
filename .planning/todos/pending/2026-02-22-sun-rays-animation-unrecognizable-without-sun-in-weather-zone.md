---
created: 2026-02-22T20:09:28.325Z
title: Sun rays animation unrecognizable without sun in weather zone
area: display
files:
  - src/display/weather_anim.py
---

## Problem

The sun rays animation in the weather zone is hard to interpret as "sunny" because there's no sun visible in the lower section — just rays radiating from nothing. The user described them as "a bit strange" and "hard to understand that the sun rays are sun rays."

The small sun icon exists in the clock zone (top-right), but the weather zone animation (bottom 24px) only shows rays without a sun body, making it look abstract/confusing.

## Solution

TBD - needs investigation. Options:
1. Replace rays with a warm golden glow/gradient emanating from top of weather zone (implying the sun is "above")
2. Add a small sun circle in the weather zone that rays emanate from
3. Replace with an entirely different sunny-day animation (warm shimmer, light particles floating upward, etc.)
