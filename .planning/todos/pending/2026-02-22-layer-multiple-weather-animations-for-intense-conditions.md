---
created: 2026-02-22T20:20:56.867Z
title: Layer multiple weather animations for intense conditions
area: general
files: []
---

## Problem

Weather animations currently play individually, but real weather involves combinations — heavy rain with wind, thunderstorms with rain, snow with fog, etc. When conditions are intense (e.g. heavy rainfall), the display should combine/layer multiple animation effects to better represent what's actually happening outside.

## Solution

- Allow animation compositor to blend multiple weather effects simultaneously
- Scale animation intensity based on actual weather data (e.g. precipitation mm/h, wind speed)
- Define combination rules: which animations can layer together and how they blend
- Heavy conditions could trigger more particles, faster movement, or additional overlay effects
