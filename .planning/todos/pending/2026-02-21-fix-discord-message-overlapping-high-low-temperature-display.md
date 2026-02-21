---
created: 2026-02-21T15:48:46.240Z
title: Fix Discord message overlapping high/low temperature display
area: display
files:
  - src/display/renderer.py
  - src/providers/discord_bot.py
---

## Problem

When a Discord message is sent to the Pixoo display, the message text renders on top of the high/low temperature indicators in the weather zone (y=40-63). The text and temperature values overlap, making both unreadable.

The current design note says "When a message is active, the precipitation indicator is hidden to make room" but the high/low line is still being drawn underneath the message text.

## Solution

TBD - needs systematic debugging to confirm exact y-coordinates and rendering order. Likely need to suppress the high/low row when a Discord message is active, or position the message text below or instead of the high/low + precipitation area.
