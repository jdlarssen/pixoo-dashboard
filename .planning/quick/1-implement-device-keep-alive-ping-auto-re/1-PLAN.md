---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/device/pixoo_client.py
  - src/main.py
  - tests/test_pixoo_client.py
  - tests/test_keepalive.py
autonomous: true
requirements: [KEEPALIVE-PING, KEEPALIVE-REBOOT, KEEPALIVE-MAIN-LOOP]
must_haves:
  truths:
    - "Device receives a lightweight health ping every ~30s when no frame push happened"
    - "After 5 consecutive device failures, bot sends Device/SysReboot command"
    - "After reboot, bot waits 30s before resuming pings"
    - "Successful frame pushes reset the ping timer and failure counter"
    - "Ping failures feed into existing health tracker for Discord alerting"
  artifacts:
    - path: "src/device/pixoo_client.py"
      provides: "ping() and reboot() methods"
      contains: "def ping"
    - path: "src/device/pixoo_client.py"
      provides: "reboot method"
      contains: "def reboot"
    - path: "src/main.py"
      provides: "Keep-alive loop integration with _PING_INTERVAL, _REBOOT_THRESHOLD"
      contains: "_PING_INTERVAL"
    - path: "tests/test_pixoo_client.py"
      provides: "TestPing and TestReboot test classes"
      contains: "class TestPing"
    - path: "tests/test_keepalive.py"
      provides: "Integration tests for ping/reboot/push interaction"
      contains: "class TestKeepAliveIntegration"
  key_links:
    - from: "src/main.py"
      to: "src/device/pixoo_client.py"
      via: "client.ping() and client.reboot() calls in main_loop"
      pattern: "client\\.ping\\(\\)|client\\.reboot\\(\\)"
    - from: "src/device/pixoo_client.py"
      to: "pixoo library"
      via: "validate_connection() for ping, _requests_module.post for reboot"
      pattern: "validate_connection|Device/SysReboot"
---

<objective>
Add device keep-alive ping and auto-reboot recovery to prevent the Divoom Pixoo 64 from disconnecting from WiFi during idle periods.

Purpose: The ESP32 inside the Pixoo 64 enters WiFi power save mode during idle periods between frame pushes, causing daily disconnections. A 30-second ping keeps the radio active, and graduated recovery (5 failures -> reboot) handles actual outages.

Output: Working ping/reboot methods on PixooClient, integrated into main_loop with health tracking, fully tested.
</objective>

<execution_context>
@/Users/jdl/.claude/get-shit-done/workflows/execute-plan.md
@/Users/jdl/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@docs/plans/2026-02-24-device-keep-alive.md (EXACT implementation code -- follow precisely)
@docs/plans/2026-02-24-device-keep-alive-design.md (Approved design rationale)
@src/device/pixoo_client.py (File to modify)
@src/main.py (File to modify)
@tests/test_pixoo_client.py (Test file to extend)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ping() and reboot() methods to PixooClient with TDD</name>
  <files>src/device/pixoo_client.py, tests/test_pixoo_client.py</files>
  <action>
Follow the EXACT code from `docs/plans/2026-02-24-device-keep-alive.md` Tasks 1 and 2.

**Step 1: Update test fixture.** In `tests/test_pixoo_client.py`, add `c._ip = "192.168.0.193"` to the existing `client` fixture (after `c._error_until = 0.0`).

**Step 2: Add TestPing class** to `tests/test_pixoo_client.py` -- copy the exact 5 tests from the implementation plan (test_ping_returns_true_on_success, test_ping_returns_false_on_network_error, test_ping_returns_false_on_oserror, test_ping_returns_none_during_cooldown, test_ping_sets_cooldown_on_failure). Run `python -m pytest tests/test_pixoo_client.py::TestPing -v` -- expect FAIL (no ping method).

**Step 3: Add TestReboot class** to `tests/test_pixoo_client.py` -- copy the exact 4 tests from the implementation plan (test_reboot_returns_true_on_success, test_reboot_returns_false_on_network_error, test_reboot_returns_false_on_timeout, test_reboot_sends_correct_command). Run `python -m pytest tests/test_pixoo_client.py::TestReboot -v` -- expect FAIL (no reboot method).

**Step 4: Implement ping() method** in `src/device/pixoo_client.py` -- add the exact `ping()` method from the plan after `push_frame()` (after line 145). Uses `self._pixoo.validate_connection()`, respects error cooldown, returns True/False/None. Run `python -m pytest tests/test_pixoo_client.py::TestPing -v` -- expect PASS (5/5).

**Step 5: Implement reboot() method** in `src/device/pixoo_client.py`:
- Add `import json` to imports
- Add `self._ip = ip` in `__init__` after `self._error_until = 0.0` (line 102)
- Add the exact `reboot()` method from the plan after `ping()`. Sends `{"Command": "Device/SysReboot"}` via `_requests_module.post` to `http://{ip}/post`.
- Run `python -m pytest tests/test_pixoo_client.py::TestReboot -v` -- expect PASS (4/4).

**Step 6: Full regression.** Run `python -m pytest tests/test_pixoo_client.py -v` -- all tests pass.
  </action>
  <verify>
    <automated>cd /Users/jdl/Documents/GitHub/divoom-hub && python -m pytest tests/test_pixoo_client.py -v</automated>
    <manual>Verify TestPing (5 tests) and TestReboot (4 tests) all pass alongside existing tests</manual>
  </verify>
  <done>PixooClient has ping() returning True/False/None and reboot() returning True/False. All 9 new tests pass. All existing tests pass with no regressions.</done>
</task>

<task type="auto">
  <name>Task 2: Integrate keep-alive into main loop and add integration tests</name>
  <files>src/main.py, tests/test_keepalive.py</files>
  <action>
Follow the EXACT code from `docs/plans/2026-02-24-device-keep-alive.md` Tasks 3 and 4.

**Step 1: Add constants** to `src/main.py` after the imports (after line 51):
```python
_PING_INTERVAL = 30
_REBOOT_THRESHOLD = 5
_REBOOT_RECOVERY_WAIT = 30
```

**Step 2: Add tracking variables** in `main_loop()` after `needs_push = False` (line 167):
```python
last_device_success: float = 0.0
consecutive_device_failures: int = 0
reboot_wait_until: float = 0.0
```

**Step 3: Update push result handling** (lines 322-333). Replace the existing `push_result` block with the version from the plan that adds `last_device_success = time.monotonic()`, `consecutive_device_failures = 0` on success, and `consecutive_device_failures += 1` on failure. Keep the existing health_tracker calls and logging.

**Step 4: Add keep-alive ping + reboot recovery block** BEFORE `time.sleep(1.0)` (line 338). Copy the exact block from the plan that:
- Checks `now_mono > reboot_wait_until` (skip during reboot recovery wait)
- If `consecutive_device_failures >= _REBOOT_THRESHOLD`: attempt `client.reboot()`, set recovery wait, reset counter
- Elif `(now_mono - last_device_success) >= _PING_INTERVAL and last_device_success > 0`: send `client.ping()`, track success/failure via health_tracker

**Step 5: Create integration tests.** Create `tests/test_keepalive.py` with the exact `TestKeepAliveIntegration` class from the plan (4 tests: test_ping_success_does_not_affect_push_timing, test_ping_failure_sets_cooldown_shared_with_push, test_push_failure_cooldown_blocks_ping, test_reboot_after_multiple_ping_failures).

**Step 6: Run full test suite.** `python -m pytest tests/ -v --timeout=30` -- all tests pass.
  </action>
  <verify>
    <automated>cd /Users/jdl/Documents/GitHub/divoom-hub && python -m pytest tests/ -v --timeout=30</automated>
    <manual>Verify all tests pass including new test_keepalive.py (4 tests). Verify main.py contains _PING_INTERVAL, _REBOOT_THRESHOLD, _REBOOT_RECOVERY_WAIT constants and the keep-alive block in main_loop.</manual>
  </verify>
  <done>Main loop pings device every 30s when idle, tracks consecutive failures, attempts reboot after 5 failures, waits 30s for recovery. All existing and new tests pass. Integration tests verify ping/push cooldown sharing and reboot-after-failure flow.</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/ -v --timeout=30` -- all tests pass (existing + 9 new pixoo_client tests + 4 keepalive integration tests)
2. `grep -n "def ping" src/device/pixoo_client.py` -- ping method exists
3. `grep -n "def reboot" src/device/pixoo_client.py` -- reboot method exists
4. `grep -n "_PING_INTERVAL" src/main.py` -- keep-alive constants exist
5. `grep -n "client.ping()" src/main.py` -- ping integrated into main loop
6. `grep -n "client.reboot()" src/main.py` -- reboot integrated into main loop
</verification>

<success_criteria>
- PixooClient.ping() sends Channel/GetAllConf (via validate_connection), returns True/False/None
- PixooClient.reboot() sends Device/SysReboot via raw HTTP POST, returns True/False
- Main loop pings every 30s when no frame push happened recently
- Frame pushes reset ping timer and failure counter
- After 5 consecutive failures, reboot is attempted with 30s recovery wait
- Health tracker receives ping success/failure events for Discord alerting
- 13 new tests pass (9 unit + 4 integration), zero regressions
</success_criteria>

<output>
After completion, create `.planning/quick/1-implement-device-keep-alive-ping-auto-re/1-SUMMARY.md`
</output>
