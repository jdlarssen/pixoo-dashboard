---
status: resolved
trigger: "Sending a Discord message containing an emoji crashes the dashboard with UnicodeEncodeError"
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED -- no sanitization of non-Latin-1 characters before BDF font rendering
test: N/A (resolved)
expecting: N/A
next_action: Archive

## Symptoms

expected: Discord messages containing emoji should display gracefully -- strip emoji and show text. Dashboard should NEVER crash from user input.
actual: Dashboard crashes with UnicodeEncodeError: 'latin-1' codec can't encode character '\U0001f604' in position 11
errors: |
  File "src/display/renderer.py", line 268, in _wrap_text
      bbox = font.getbbox(test_line)
  UnicodeEncodeError: 'latin-1' codec can't encode character '\U0001f604' in position 11: ordinal not in range(256)
reproduction: Send any Discord message containing an emoji character to the configured channel.
started: First time testing Discord messages with emoji. BDF fonts only support Latin-1.

## Eliminated

(none -- root cause confirmed on first hypothesis)

## Evidence

- timestamp: 2026-02-21T00:01:00Z
  checked: Full data flow from discord_bot.py -> MessageBridge -> main.py -> DisplayState -> renderer.py
  found: Zero sanitization of message text anywhere. Discord content goes raw from message.content.strip() through bridge.set_message(content) to DisplayState.message_text to _render_message() to _wrap_text() where font.getbbox() crashes on non-Latin-1 chars.
  implication: Root cause confirmed -- no defensive filtering exists. Any character outside Latin-1 (code point > 255) will crash the renderer.

- timestamp: 2026-02-21T00:03:00Z
  checked: Fix implementation and verification
  found: Added sanitize_for_bdf() in discord_bot.py (primary layer) and _sanitize_for_font() in renderer.py (defensive fallback). 135/135 tests pass including 23 new tests covering emoji, CJK, all-emoji, Norwegian chars, boundary cases.
  implication: Fix verified -- emoji messages no longer crash. Text portion is preserved, emoji stripped silently.

## Resolution

root_cause: No sanitization of Discord message text before passing to BDF font rendering. BDF fonts only support Latin-1 (code points 0-255). font.getbbox() in _wrap_text() raises UnicodeEncodeError when encountering emoji or other non-Latin-1 characters. The unhandled exception kills the main rendering loop.
fix: Two-layer defense. (1) Primary: sanitize_for_bdf() in MessageBridge.set_message() strips all characters with code points > 255 before storage. All-emoji messages become None (cleared). (2) Defensive: _sanitize_for_font() in renderer._wrap_text() strips non-Latin-1 characters as a fallback for any future code path. Whitespace is collapsed after stripping.
verification: 135/135 tests pass (0 regressions). 23 new tests: 13 for sanitize_for_bdf(), 5 for MessageBridge integration, 5 for renderer emoji safety. Covers emoji, CJK, flag emoji, all-emoji, Norwegian chars, Latin-1 boundary, empty/whitespace edge cases.
files_changed:
  - src/providers/discord_bot.py
  - src/display/renderer.py
  - tests/test_discord_bot.py
  - tests/test_renderer.py
