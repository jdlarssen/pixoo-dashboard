---
status: resolved
trigger: "Discord message text overlaps high/low temperature display in the weather zone"
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: All 104 tests pass, pixel math verified
expecting: N/A
next_action: Archive

## Symptoms

expected: Discord message should not overlap the high/low temperature values
actual: Discord message text renders on top of the high/low temperature line in the weather zone
errors: No errors - visual overlap issue only
reproduction: Send any text message to the configured Discord channel while the dashboard is running
started: First time testing - Discord bot was just set up. Never worked correctly.

## Eliminated

## Evidence

- timestamp: 2026-02-21T00:01:00Z
  checked: renderer.py _render_message function and render_weather_zone
  found: |
    Weather zone starts at y=40.
    High/low text drawn at (TEXT_X, zone_y + 10) = (2, 50) with tiny font (4x6), occupying y=50 to y=55.
    Message text drawn at start_y = zone_y + 12 = 52 with tiny font (4x6), occupying y=52 to y=57.
    Overlap: hilo y=50-55 and message y=52-57 share pixels y=52-55 (4 pixel rows of overlap).
  implication: The message start_y offset of +12 is too close to the hilo offset of +10. Need to push message below hilo or suppress hilo.

- timestamp: 2026-02-21T00:02:00Z
  checked: Rain indicator already suppressed when message active (line 192)
  found: Pattern exists - rain is suppressed with `if state.message_text is None`
  implication: Extending this pattern to hilo is consistent with the existing design.

## Resolution

root_cause: In _render_message (renderer.py), start_y = zone_y + 12 placed message text at y=52, which overlapped the high/low temperature text at y=50 (zone_y + 10) since the tiny font is 6px tall. The message and hilo shared 4 pixel rows (y=52-55).
fix: |
  Two changes in renderer.py:
  1. Suppress high/low rendering when Discord message is active (same pattern as rain suppression)
  2. Move message start_y from zone_y + 12 to zone_y + 10 (takes over the hilo position)
  This gives the message 2 full lines (y=50-55 and y=57-62) within the 24px weather zone,
  while keeping current temp visible at y=41-48. No overlap.
verification: All 104 tests pass. Pixel math verified - no overlap in either message-active or message-inactive states.
files_changed:
  - src/display/renderer.py
