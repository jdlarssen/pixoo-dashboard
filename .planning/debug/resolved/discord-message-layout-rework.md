---
status: resolved
trigger: "Three layout issues with Discord message in the weather zone need fixing together."
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:00:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED -- 3 issues all in renderer.py render_weather_zone / _render_message
test: All 3 issues traced to exact lines
expecting: Fix will resolve all 3 layout issues
next_action: Apply fix to renderer.py

## Symptoms

expected: |
  When Discord message IS active:
  1. Message text supports 3 lines, starts from FIRST line of message area (not 2nd)
  2. High/low temps remain visible (not suppressed)
  3. Rain indicator positioned BELOW high/low line
  Message at x=22..63, temp/hilo/precip on left side.
  When NO message: same except rain moves below high/low.
actual: |
  1. Message starts on 2nd line (blank space above)
  2. High/low suppressed when message active
  3. Rain indicator above/beside high/low instead of below
errors: No errors -- visual layout issues only.
reproduction: Send any text to Discord channel while dashboard running.
started: Previous two fix attempts (commits e00ffc1, d6bec03).

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-02-21T00:01:00Z
  checked: renderer.py line 184 -- high/low guard
  found: Guard `if state.message_text is None` suppresses hilo when message active
  implication: Issue #2 root cause -- remove the message_text guard from hilo rendering

- timestamp: 2026-02-21T00:01:00Z
  checked: renderer.py lines 194-204 -- rain indicator position
  found: Rain drawn at (TEXT_X + temp_width + 5, zone_y + 2) -- BESIDE temp, not below hilo
  implication: Issue #3 root cause -- move rain to (TEXT_X, zone_y + 17) below hilo, remove message guard

- timestamp: 2026-02-21T00:01:00Z
  checked: renderer.py _render_message lines 242-243 -- message start position
  found: start_y = zone_y + 10 and only 2 lines rendered (lines[:2])
  implication: Issue #1 root cause -- change start_y to zone_y + 1 and allow 3 lines (lines[:3])

## Resolution

root_cause: |
  Three issues in renderer.py render_weather_zone and _render_message:
  1. _render_message uses start_y=zone_y+10 (should be zone_y+1) and limits to 2 lines (should be 3)
  2. High/low rendering guarded by `message_text is None` (should always render)
  3. Rain indicator at (beside temp, zone_y+2) should be at (TEXT_X, zone_y+17) below hilo
fix: |
  Four changes in src/display/renderer.py:
  1. Removed `state.message_text is None` guard from high/low rendering (line 184) -- hilo now always visible
  2. Moved rain indicator from beside temp (TEXT_X+temp_width+5, zone_y+2) to below hilo (TEXT_X, zone_y+17)
  3. Removed `state.message_text is None` guard from rain indicator -- precip now always visible
  4. Changed _render_message: start_y from zone_y+10 to zone_y+1, max lines from 2 to 3
  5. Updated _wrap_text truncation from hardcoded 2 lines to max_lines=3
verification: All 104 tests pass (0 failures). Rain indicator test confirms pixels in y=51..64 (rain at y=57 fits).
files_changed:
  - src/display/renderer.py
