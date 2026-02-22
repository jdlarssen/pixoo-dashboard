---
created: 2026-02-22T20:20:56.867Z
title: Seasonal night mode with real sunset sunrise times
area: general
files: []
---

## Problem

Night mode currently uses fixed times regardless of season. In reality, sunset varies dramatically throughout the year — around 4-5pm in December vs 8-9pm in June. The display should reflect the actual night duration for the user's location so the night mode transition feels natural and seasonally accurate.

## Solution

- Use astronomical sunset/sunrise calculation based on the user's latitude/longitude and current date
- Libraries like `suncalc` can compute precise sunrise/sunset times for any date and location
- Transition night mode on/off based on these computed times instead of hardcoded hours
- Consider civil twilight (sun 6° below horizon) for a more gradual transition
