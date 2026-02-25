---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/device/pixoo_client.py
  - tests/test_pixoo_client.py
autonomous: true
requirements: [QUICK-2]
must_haves:
  truths:
    - "After a device error, cooldown starts at 3 seconds"
    - "Each consecutive failure doubles the cooldown (3s -> 6s -> 12s -> 24s -> 48s -> 60s)"
    - "Cooldown never exceeds 60 seconds"
    - "Any successful device communication resets cooldown back to 3 seconds"
    - "Existing push_frame/ping/reboot return values and behavior are unchanged"
  artifacts:
    - path: "src/device/pixoo_client.py"
      provides: "Exponential backoff cooldown logic"
      contains: "_ERROR_COOLDOWN_BASE"
    - path: "tests/test_pixoo_client.py"
      provides: "Tests for exponential backoff behavior"
      contains: "TestExponentialBackoff"
  key_links:
    - from: "src/device/pixoo_client.py"
      to: "src/main.py"
      via: "push_frame()/ping() return values unchanged"
      pattern: "push_result is (True|False|None)"
---

<objective>
Replace the constant 3-second error cooldown in PixooClient with exponential backoff.

Purpose: When the device goes offline, the current constant 3s cooldown causes the main loop to retry every ~3 seconds indefinitely, generating noisy logs and wasting CPU cycles on a device that may be down for minutes. Exponential backoff (3s -> 6s -> 12s -> ... -> 60s cap) reduces retry noise and gives the device more time to recover on each consecutive failure.

Output: Updated PixooClient with backoff state, updated tests.
</objective>

<execution_context>
@/Users/jdl/.claude/get-shit-done/workflows/execute-plan.md
@/Users/jdl/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/device/pixoo_client.py
@tests/test_pixoo_client.py
@tests/test_keepalive.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add exponential backoff state and logic to PixooClient</name>
  <files>src/device/pixoo_client.py</files>
  <action>
Replace the constant `_ERROR_COOLDOWN = 3.0` with three module-level constants:

```python
_ERROR_COOLDOWN_BASE = 3.0   # initial cooldown after first failure
_ERROR_COOLDOWN_MAX = 60.0   # maximum cooldown cap
```

Add a new instance attribute in `__init__`:

```python
self._current_cooldown: float = _ERROR_COOLDOWN_BASE
```

In `push_frame()`:
- On failure (the except block), use `self._current_cooldown` instead of `_ERROR_COOLDOWN`:
  ```python
  self._error_until = time.monotonic() + self._current_cooldown
  logger.info("Device cooldown: pausing pushes for %.0fs (backoff)", self._current_cooldown)
  self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
  ```
  Note: set `_error_until` FIRST with the current value, THEN double for next time.
- On success (after `self._pixoo.push()` succeeds, before `return True`), reset backoff:
  ```python
  self._current_cooldown = _ERROR_COOLDOWN_BASE
  ```

In `ping()`:
- On failure (the except block), same pattern:
  ```python
  self._error_until = time.monotonic() + self._current_cooldown
  self._current_cooldown = min(self._current_cooldown * 2, _ERROR_COOLDOWN_MAX)
  ```
- On success (before `return True`), reset:
  ```python
  self._current_cooldown = _ERROR_COOLDOWN_BASE
  ```

Do NOT change the `reboot()` method -- it has its own error handling and does not use cooldown.
Do NOT change `set_brightness()` -- it does not participate in cooldown.
Do NOT change `test_connection()` -- it delegates to `push_frame()` which handles backoff.
Do NOT change any return values or method signatures.

Remove the old `_ERROR_COOLDOWN` constant entirely (replace all references with the new names).
  </action>
  <verify>
```
cd /Users/jdl/Documents/GitHub/divoom-hub && python -c "
from unittest.mock import MagicMock, patch
from requests.exceptions import ConnectionError
with patch('src.device.pixoo_client.PixooClient.__init__', lambda self, *a, **kw: None):
    from src.device.pixoo_client import PixooClient, _ERROR_COOLDOWN_BASE, _ERROR_COOLDOWN_MAX
    c = object.__new__(PixooClient)
    c._pixoo = MagicMock()
    c._size = 64
    c._last_push_time = 0.0
    c._error_until = 0.0
    c._ip = '192.168.0.193'
    c._current_cooldown = _ERROR_COOLDOWN_BASE
    assert _ERROR_COOLDOWN_BASE == 3.0
    assert _ERROR_COOLDOWN_MAX == 60.0
    assert c._current_cooldown == 3.0
    # Simulate failure
    c._pixoo.push.side_effect = ConnectionError('refused')
    from PIL import Image
    img = Image.new('RGB', (64, 64), (0,0,0))
    c.push_frame(img)
    assert c._current_cooldown == 6.0, f'Expected 6.0, got {c._current_cooldown}'
    print('OK: backoff constants and doubling verified')
"
```
  </verify>
  <done>PixooClient uses exponential backoff: _current_cooldown starts at 3s, doubles on each consecutive failure (capped at 60s), resets to 3s on any success. Old _ERROR_COOLDOWN constant removed.</done>
</task>

<task type="auto">
  <name>Task 2: Add exponential backoff tests</name>
  <files>tests/test_pixoo_client.py</files>
  <action>
Add a new test class `TestExponentialBackoff` to `tests/test_pixoo_client.py` after the existing `TestPing` class. Use the existing `client` fixture (which already sets `_error_until = 0.0`). Update the fixture to also set `_current_cooldown` to `_ERROR_COOLDOWN_BASE` (import it at the top of the file).

Import at top of file:
```python
from src.device.pixoo_client import PixooClient, _ERROR_COOLDOWN_BASE, _ERROR_COOLDOWN_MAX
```
(Replace the existing `from src.device.pixoo_client import PixooClient` line.)

Update the `client` fixture to add:
```python
c._current_cooldown = _ERROR_COOLDOWN_BASE
```

Also update `tests/test_keepalive.py` client fixture the same way (add `_current_cooldown` attribute, import the constant).

Tests to add in `TestExponentialBackoff`:

1. `test_first_failure_uses_base_cooldown` -- After one push_frame failure, `_error_until` should be ~3s from now (within tolerance). `_current_cooldown` should be 6.0 (doubled for next time).

2. `test_consecutive_failures_double_cooldown` -- Clear `_error_until` between failures, trigger 4 consecutive push_frame failures. After each, verify `_current_cooldown` is: 6, 12, 24, 48.

3. `test_cooldown_caps_at_max` -- Set `_current_cooldown = 48.0`, trigger failure. Verify `_current_cooldown` becomes 60.0 (not 96). Trigger another failure (after clearing cooldown). Verify stays at 60.0.

4. `test_success_resets_cooldown_to_base` -- Set `_current_cooldown = 24.0` (simulating prior failures). Do a successful push_frame. Verify `_current_cooldown` is back to `_ERROR_COOLDOWN_BASE` (3.0).

5. `test_ping_failure_also_increases_backoff` -- Trigger ping failure. Verify `_current_cooldown` doubled.

6. `test_ping_success_resets_backoff` -- Set `_current_cooldown = 24.0`. Successful ping. Verify reset to base.

7. `test_backoff_shared_between_push_and_ping` -- Push fails (cooldown doubles to 6), clear cooldown, ping fails (cooldown doubles to 12). Verifies both methods share the same backoff state.

Each test should clear `_error_until = 0.0` and `_last_push_time = 0.0` before triggering failures to bypass rate limiting and cooldown checks.
  </action>
  <verify>cd /Users/jdl/Documents/GitHub/divoom-hub && python -m pytest tests/test_pixoo_client.py tests/test_keepalive.py -v --tb=short 2>&1 | tail -40</verify>
  <done>All existing tests still pass. New TestExponentialBackoff class has 7 tests covering: base cooldown, consecutive doubling, cap at 60s, reset on success, ping backoff, shared state between push and ping. test_keepalive.py also passes with updated fixture.</done>
</task>

</tasks>

<verification>
Run the full test suite to confirm nothing is broken:
```
cd /Users/jdl/Documents/GitHub/divoom-hub && python -m pytest tests/ -v --tb=short
```

All tests pass, including:
- Existing push_frame error handling tests (unchanged behavior)
- Existing ping/reboot tests (unchanged behavior)
- Existing keepalive integration tests (unchanged behavior)
- New exponential backoff tests (7 new tests)
</verification>

<success_criteria>
- `_ERROR_COOLDOWN` constant is replaced with `_ERROR_COOLDOWN_BASE` (3.0) and `_ERROR_COOLDOWN_MAX` (60.0)
- PixooClient has `_current_cooldown` instance attribute
- Each consecutive failure doubles the cooldown: 3 -> 6 -> 12 -> 24 -> 48 -> 60 (capped)
- Any successful push_frame or ping resets cooldown to 3s
- All existing tests pass without modification (except fixture update for new attribute)
- 7 new backoff-specific tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/2-add-exponential-backoff-for-device-recon/2-SUMMARY.md`
</output>
