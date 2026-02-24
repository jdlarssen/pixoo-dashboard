---
status: resolved
trigger: "Divoom Pixoo device went offline at 20:18. Display stuck showing 20:18. Main loop retrying with 3s cooldowns but never recovered. No Discord notification sent about device being unreachable."
created: 2026-02-24T20:30:00Z
updated: 2026-02-24T20:45:00Z
---

## Current Focus

hypothesis: CONFIRMED -- push_frame() swallows all exceptions internally, so main_loop never reaches the except block. record_failure("device") is never called; record_success("device") is called even on failure. Additionally, "Pushed frame" log is outside the try/except, logging unconditionally on state_changed.
test: Code trace confirms the control flow
expecting: N/A -- root cause found
next_action: Done -- archive session

## Symptoms

expected: Display updates every minute. When device is unreachable for extended period, Discord notification is sent.
actual: Display stuck at 20:18. Continuous ConnectTimeoutError with 3s cooldowns, escalating to "Host is down" (Errno 64). No Discord message was sent.
errors:
- ConnectTimeoutError at 20:18:34, 20:18:42, 20:18:51, 20:18:59
- ConnectTimeoutError at 20:19:07, 20:19:15, 20:19:23
- NewConnectionError (Host is down) at 20:19:26, 20:19:29
- Log says "Pushed frame: 20:19" at 20:19:00 and 20:19:24 but device was unreachable
- No Discord log entry at any point
reproduction: Device went offline on network (WiFi issue or device powered off)
timeline: Working normally until 20:18:21 (last successful push). Failures started at 20:18:34. Logs end at 20:19:29.

## Eliminated

## Evidence

- timestamp: 2026-02-24T20:32:00Z
  checked: pixoo_client.py push_frame() exception handling (lines 131-138)
  found: push_frame() catches (RequestException, OSError) and returns silently. Does NOT re-raise. The main_loop try/except wrapping push_frame() can never catch device errors.
  implication: main_loop except block at line 326 is dead code for device communication errors.

- timestamp: 2026-02-24T20:33:00Z
  checked: main.py main_loop push handling (lines 322-332)
  found: record_success("device") is on the try path at line 325. Since push_frame() never raises, this always executes -- even after a failed push. record_failure("device") at line 329 is unreachable.
  implication: HealthTracker thinks device is always healthy. Never accumulates failures. Never triggers alert threshold (5 consecutive failures for device). This is why no Discord notification was sent.

- timestamp: 2026-02-24T20:34:00Z
  checked: main.py "Pushed frame" log at line 331
  found: The log "Pushed frame: %s %s" is OUTSIDE the try/except block (after it). It fires whenever state_changed is True, regardless of push success/failure.
  implication: Log is misleading -- shows "Pushed frame: 20:19" even though the push failed. This is Bug 1.

- timestamp: 2026-02-24T20:35:00Z
  checked: pixoo_client.py cooldown return path (lines 123-124)
  found: When in error cooldown, push_frame() returns immediately without raising. Main loop still calls record_success() after this no-op return.
  implication: Even during active cooldown period, every loop iteration records "success" -- resetting any failure count that might have accumulated (if it ever could).

## Resolution

root_cause: push_frame() in pixoo_client.py catches all device errors internally and returns silently, preventing main_loop from detecting failures. As a result: (1) health_tracker.record_failure("device") is never called (dead code), so Discord alerts never trigger. (2) health_tracker.record_success("device") is called even after failed pushes, keeping the tracker in perpetual "healthy" state. (3) The "Pushed frame" log is outside the try/except, appearing even after failed pushes.
fix: Changed push_frame() to return tri-state (True/False/None) instead of void. True = delivered, False = communication error, None = skipped (rate limit/cooldown). Updated main_loop to use `push_result is True` for record_success, `push_result is False` for record_failure, and no action for None. Moved "Pushed frame" log inside the success branch. Updated test_connection() to check `result is True`.
verification: All 244 tests pass (238 original + 6 new regression tests). New tests verify: True on success, False on network error, False on OSError, None during cooldown, None when rate limited, and caller can distinguish all three states.
files_changed:
- src/device/pixoo_client.py
- src/main.py
- tests/test_pixoo_client.py
