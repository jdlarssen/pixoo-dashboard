---
status: resolved
trigger: "pixoo-push-frame-timeout - ReadTimeout propagates uncaught from pixoo_client.py through main_loop and kills the process"
created: 2026-02-22T00:00:00Z
updated: 2026-02-22T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - push_frame() and set_brightness() had no try/except for network errors.
test: 12 unit tests written and passing (TDD approach)
expecting: All 203 tests pass, zero regressions
next_action: Archive session

## Symptoms

expected: The dashboard should run 24/7 without crashing. When the Pixoo device is temporarily unreachable, it should log a warning and retry on the next loop iteration.
actual: The entire process crashes with an uncaught ReadTimeout exception.
errors: requests.exceptions.ReadTimeout: HTTPConnectionPool(host='192.168.0.193', port=80): Read timed out. (read timeout=None). Call chain: main_loop -> push_frame (pixoo_client.py:70) -> pixoo.push() -> __send_buffer -> requests.post (no timeout set)
reproduction: Run the dashboard against a Pixoo device that becomes unresponsive (network hiccup, device sleeping, etc.)
started: Can happen anytime the device is unreachable during a frame push.

## Eliminated

(none - root cause was confirmed on first hypothesis)

## Evidence

- timestamp: 2026-02-22T00:01:00Z
  checked: pixoo_client.py push_frame() method (lines 50-71)
  found: No try/except around self._pixoo.draw_image(image) (line 69) or self._pixoo.push() (line 70). Any network exception propagates uncaught.
  implication: CONFIRMED - push_frame is vulnerable to network errors.

- timestamp: 2026-02-22T00:01:00Z
  checked: pixoo_client.py set_brightness() method (lines 73-84)
  found: No try/except around self._pixoo.set_brightness(capped) (line 84). Same vulnerability.
  implication: CONFIRMED - set_brightness is also vulnerable to network errors.

- timestamp: 2026-02-22T00:01:00Z
  checked: main.py main_loop (lines 247-248 and 285)
  found: client.set_brightness(target_brightness) at line 248 and client.push_frame(frame) at line 285 are called without any try/except.
  implication: CONFIRMED - main_loop has no error handling for device communication failures either.

- timestamp: 2026-02-22T00:01:00Z
  checked: pixoo_client.py test_connection() method (lines 86-98)
  found: test_connection() DOES have try/except wrapping push_frame(). This shows the pattern was understood but not applied to push_frame/set_brightness themselves.
  implication: The defensive pattern exists in the codebase but was not applied to the hot-path methods.

- timestamp: 2026-02-22T00:02:00Z
  checked: pixoo library internals (Pixoo.push -> __send_buffer, Pixoo.set_brightness)
  found: Both call requests.post() with no timeout parameter and no try/except. Confirmed these are the exact HTTP calls that raise ReadTimeout and ConnectionError.
  implication: The vulnerability originates in the third-party library; our wrapper must handle it.

## Resolution

root_cause: PixooClient.push_frame() and PixooClient.set_brightness() did not catch network exceptions (ReadTimeout, ConnectionError, OSError, etc.). When the Pixoo device becomes unreachable, requests.post() inside the pixoo library raises these exceptions, which propagate uncaught through main_loop() and crash the entire dashboard process.
fix: Added try/except (RequestException, OSError) to both push_frame() and set_brightness() in pixoo_client.py. Errors are logged as warnings and the methods return gracefully. push_frame() also avoids updating _last_push_time on failure so the next iteration retries immediately.
verification: 12 new tests pass (TDD: written first, confirmed failing, then fixed). Full suite 203/203 pass. Ruff lint clean.
files_changed:
  - src/device/pixoo_client.py
  - tests/test_pixoo_client.py
