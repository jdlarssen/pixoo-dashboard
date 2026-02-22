---
status: resolved
trigger: "Divoom Pixoo 64 display freezes after ~8 minutes of operation. Connection reset error observed."
created: 2026-02-22T22:40:00-06:00
updated: 2026-02-22T22:55:00-06:00
---

## Current Focus

hypothesis: CONFIRMED and FIXED
test: All 205 tests pass including 3 new tests for cooldown and rate limiting
expecting: Device no longer overwhelmed at 1 FPS; timeouts prevent indefinite hangs
next_action: Archive session

## Symptoms

expected: Dashboard runs continuously, pushing frames every ~60s to the Pixoo 64 display without interruption.
actual: After ~8 minutes of normal operation, the device connection resets and the display freezes. The app may recover briefly but then stops.
errors: |
  2026-02-22 22:34:44,031 [src.device.pixoo_client] Device communication error during push_frame: ('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer'))
reproduction: Start the dashboard with `.venv/bin/python src/main.py`. Wait ~8 minutes. Display freezes.
started: This session. Started at 22:28, error at 22:34:44, display frozen by 22:36.

## Eliminated

- hypothesis: Stale TCP connection from requests connection pooling
  evidence: pixoo library uses bare requests.post() (not Session), each call creates fresh connection. ConnectionResetError(54) indicates device actively reset, not stale connection.
  timestamp: 2026-02-22T22:44:00

- hypothesis: Bus/weather API blocking causing the 2.5min gap alone
  evidence: Bus timeout max = 20s (2x 10s), weather not due until 22:38. The 150s gap requires device-side blocking. The pixoo library's requests.post() to device has NO timeout -- a device hang causes indefinite blocking.
  timestamp: 2026-02-22T22:47:00

## Evidence

- timestamp: 2026-02-22T22:42:00
  checked: pixoo library __send_buffer and __reset_counter
  found: |
    The pixoo library has a `__refresh_counter_limit = 32` and resets the counter when it reaches 32.
    With animation active (0.35s sleep = ~3 FPS), the counter hits 32 every ~11 seconds.
    Each reset sends a `Draw/ResetHttpGifId` HTTP POST to the device.
    The reset call has NO timeout and NO error handling in the pixoo library.
  implication: Device-level HTTP hangs propagate to indefinite main loop blocks.

- timestamp: 2026-02-22T22:43:00
  checked: main_loop architecture and frame push frequency
  found: |
    When weather_anim is not None, the loop sleeps 0.35s and pushes EVERY iteration.
    This produces ~3 requests/second to the device's embedded HTTP server.
    "Pushed frame" log ONLY fires on state_changed, so animation pushes are silent.
    The 2.5min log gap represents the main loop BLOCKED on a device HTTP call.
  implication: Silent animation pushes at 3 FPS overwhelm the device, then a hung request blocks the loop.

- timestamp: 2026-02-22T22:44:00
  checked: pixoo library requests usage - no timeouts
  found: |
    ALL pixoo library HTTP calls to the device use bare `requests.post()` with NO timeout.
    If the device's HTTP server hangs (overwhelmed), the call blocks forever.
    TCP default timeout on macOS is ~75-120 seconds, explaining the 2.5min gap.
  implication: Device overwhelm -> HTTP hang -> blocks for TCP timeout -> ConnectionResetError(54)

- timestamp: 2026-02-22T22:46:00
  checked: Known Pixoo 64 device limitations (web research)
  found: |
    DOCUMENTED: "Try to not call the push() method more than once per second"
    Device cannot handle >1 req/sec reliably. Device freezes after ~300 rapid pushes.
    At 3 FPS: 300 pushes in ~100 seconds, well within the 8-minute failure window.
  implication: 3 FPS animation rate is 3x beyond the device's documented capacity.

## Resolution

root_cause: |
  TWO compounding issues:

  1. FRAME RATE TOO HIGH: Weather animation pushed frames at ~3 FPS (0.35s sleep),
     but the Pixoo 64 can only reliably handle ~1 push/second. At 3 FPS, the device's
     embedded HTTP server was overwhelmed within minutes (~1400 requests in 8 min),
     causing ConnectionResetError(54) as the device dropped connections.

  2. NO TIMEOUT ON DEVICE HTTP CALLS: The pixoo library's requests.post() calls have
     no timeout. When the overwhelmed device hung, the main loop blocked indefinitely
     (until TCP timeout ~120s). The 2.5-minute log gap was this hang. After recovery,
     the device remained unstable, and another hung call at 22:36:15 froze the app
     permanently.

fix: |
  Three changes in pixoo_client.py:
  1. Monkey-patch requests.post to inject 5s timeout for device HTTP calls
     (prevents indefinite hangs when device is unresponsive)
  2. Increase minimum push interval from 0.3s to 1.0s (matching device capacity)
  3. Add 3-second error cooldown after device communication failures
     (prevents rapid retry hammering that worsens device state)

  One change in main.py:
  4. Change animation sleep from 0.35s to 1.0s (1 FPS instead of 3 FPS)
     (stays within the device's documented ~1 push/second limit)

verification: |
  - All 205 tests pass (3 new: cooldown skip, rate limit, recovery after cooldown)
  - Syntax check passes on both modified files
  - Import chain verified (PixooClient, _patch_requests_post, constants)
  - Monkey-patch logic verified: only targets device URLs (http://192.*), preserves existing timeouts
  - At 1 FPS: ~480 pushes in 8 min (vs ~1400 before), ~15 counter resets (vs ~44)
  - With 5s timeout: worst-case hang is 5s, not 120s

files_changed:
  - src/device/pixoo_client.py
  - src/main.py
  - tests/test_pixoo_client.py
