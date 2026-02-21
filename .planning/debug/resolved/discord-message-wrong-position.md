---
status: resolved
trigger: "Discord message text is positioned incorrectly in the weather zone — starts from left side, should be bottom-middle/right"
created: 2026-02-21T17:30:00+01:00
updated: 2026-02-21T17:40:00+01:00
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: Visual rendering + 104/104 tests passing
expecting: N/A
next_action: Archive

## Symptoms

expected: Discord message should appear in positions 8,9 of a 3x3 grid within the weather zone (y=40-63). That means bottom-middle and bottom-right: approximately x=22-63, y=56-63. Same height as temperature line but shifted right.
actual: Message text starts from the left edge (x=TEXT_X=2) at y=zone_y+10 (y=50). Overlaps with weather content horizontally.
errors: No errors — visual positioning issue only.
reproduction: Send any text message to the configured Discord channel while dashboard is running.
started: Since initial implementation. Previous fix (e00ffc1) addressed vertical overlap but not horizontal position.

## Eliminated

## Evidence

- timestamp: 2026-02-21T17:35:00+01:00
  checked: _render_message() in renderer.py lines 214-247
  found: Message draws at (TEXT_X, zone_y+10) = (2, 50) for line 1 and (2, 57) for line 2. max_width = 64 - TEXT_X - 1 = 61px. This places the message at the far-left of the display, spanning nearly the full width.
  implication: Both x-position and max_width need to change for positions 8,9.

- timestamp: 2026-02-21T17:36:00+01:00
  checked: Visual rendering output (pixel dump and 10x scaled PNG)
  found: Temperature "8" occupies x=2-5, y=42-47 (top-left). Message "Hello from" starts at x=2, y=50 and "Discord" at x=2, y=57. Message overlaps horizontally with the area directly below the temperature.
  implication: Message x-position must shift right to ~22px to occupy middle+right columns of weather zone grid.

- timestamp: 2026-02-21T17:40:00+01:00
  checked: Post-fix visual rendering and full test suite
  found: Message now renders at x=22-60 (y=50-61), temperature remains at x=2-5 (y=42-47). No horizontal overlap. All 104 tests pass. Long messages truncate correctly with "..." at the narrower 41px width.
  implication: Fix verified — message occupies positions 8,9 of weather zone grid as requested.

## Resolution

root_cause: _render_message() used TEXT_X (2px) as the x-position for all message text. This placed the Discord message at the far-left of the display (x=2), directly below the temperature reading, instead of in the bottom-middle/right area (positions 8,9 of the weather zone 3x3 grid). The max_width was also based on TEXT_X, making lines span nearly the full 64px width.
fix: Added MESSAGE_X = 22 constant in layout.py (middle column of weather zone grid). Updated _render_message() in renderer.py to use MESSAGE_X for both the x draw position and the max_width calculation (64 - 22 - 1 = 41px). Message now renders in the bottom-middle/right area of the weather zone.
verification: Visual pixel dump confirms message at x=22-60, y=50-61. Temperature at x=2-5, y=42-47. No overlap. 104/104 tests pass. Long message truncation with "..." works at narrower width.
files_changed:
  - src/display/layout.py (added MESSAGE_X = 22)
  - src/display/renderer.py (import MESSAGE_X, use in _render_message())
