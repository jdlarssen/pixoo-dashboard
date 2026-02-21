---
created: 2026-02-21T15:55:03.761Z
title: Emoji in Discord message crashes dashboard
area: display
files:
  - src/display/renderer.py:268
  - src/display/renderer.py:234
  - src/providers/discord_bot.py
---

## Problem

Sending a Discord message containing an emoji (e.g. "Klaebo vant UL-gull!!! :grinning_face_with_smiling_eyes:") crashes the entire dashboard with a `UnicodeEncodeError`. The BDF bitmap font's `getbbox()` method cannot handle characters outside Latin-1 range.

Traceback:
```
UnicodeEncodeError: 'latin-1' codec can't encode character '\U0001f604' in position 11: ordinal not in range(256)
```

Call chain: `render_frame` -> `render_weather_zone` -> `_render_message` -> `_wrap_text` -> `font.getbbox(test_line)` crashes because BDF fonts only support Latin-1 characters.

This is a crash bug — the entire dashboard goes down, not just the message display.

## Solution

TBD - needs investigation. Likely options: strip non-Latin-1 characters before rendering, or catch the error in `_render_message` and display a sanitized version.
