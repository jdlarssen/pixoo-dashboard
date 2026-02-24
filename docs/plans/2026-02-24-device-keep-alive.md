# Device Keep-Alive + Auto-Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent Divoom Pixoo 64 daily WiFi disconnections by sending periodic keep-alive pings and auto-rebooting the device on persistent failure.

**Architecture:** Add `ping()` and `reboot()` methods to `PixooClient`, then integrate a 30-second keep-alive cycle into the existing synchronous main loop. Consecutive failures trigger graduated recovery (cooldown → reboot → Discord alert).

**Tech Stack:** Python, requests (already patched with timeout), pixoo library internals (`Channel/GetAllConf`, `Device/SysReboot` commands)

---

### Task 1: Add `ping()` method to PixooClient

**Files:**
- Modify: `src/device/pixoo_client.py:56-178`
- Test: `tests/test_pixoo_client.py`

**Step 1: Write the failing tests**

Add to `tests/test_pixoo_client.py`:

```python
class TestPing:
    """ping() sends a lightweight health check to keep the device's WiFi alive."""

    def test_ping_returns_true_on_success(self, client):
        """Successful ping returns True."""
        client._pixoo.validate_connection.return_value = True
        assert client.ping() is True

    def test_ping_returns_false_on_network_error(self, client):
        """Network error during ping returns False."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        assert client.ping() is False

    def test_ping_returns_false_on_oserror(self, client):
        """OSError (host down) during ping returns False."""
        client._pixoo.validate_connection.side_effect = OSError("Host is down")
        assert client.ping() is False

    def test_ping_returns_none_during_cooldown(self, client):
        """Ping is skipped during error cooldown."""
        import time
        client._error_until = time.monotonic() + 60
        assert client.ping() is None
        client._pixoo.validate_connection.assert_not_called()

    def test_ping_sets_cooldown_on_failure(self, client):
        """Failed ping activates error cooldown."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        client.ping()
        assert client._error_until > 0
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pixoo_client.py::TestPing -v`
Expected: FAIL — `PixooClient` has no `ping()` method

**Step 3: Write minimal implementation**

Add to `src/device/pixoo_client.py` after `push_frame()` method (after line 145):

```python
    def ping(self) -> bool | None:
        """Send a lightweight health-check to keep the device WiFi alive.

        Uses Channel/GetAllConf which returns device config without any
        visual side-effect. Respects error cooldown.

        Returns:
            True if device responded, False on communication error,
            None if skipped (error cooldown active).
        """
        now = time.monotonic()
        if now < self._error_until:
            return None

        try:
            self._pixoo.validate_connection()
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device ping failed: %s", exc)
            self._error_until = time.monotonic() + _ERROR_COOLDOWN
            return False
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pixoo_client.py::TestPing -v`
Expected: PASS (5/5)

**Step 5: Run full test suite**

Run: `python -m pytest tests/test_pixoo_client.py -v`
Expected: All tests pass, no regressions

**Step 6: Commit**

```bash
git add src/device/pixoo_client.py tests/test_pixoo_client.py
git commit -m "feat: add ping() keep-alive method to PixooClient"
```

---

### Task 2: Add `reboot()` method to PixooClient

**Files:**
- Modify: `src/device/pixoo_client.py`
- Test: `tests/test_pixoo_client.py`

**Step 1: Write the failing tests**

Add to `tests/test_pixoo_client.py`:

```python
class TestReboot:
    """reboot() sends Device/SysReboot to force the device to restart."""

    def test_reboot_returns_true_on_success(self, client):
        """Successful reboot command returns True."""
        client._ip = "192.168.0.193"
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert client.reboot() is True

    def test_reboot_returns_false_on_network_error(self, client):
        """Network error during reboot returns False."""
        client._ip = "192.168.0.193"
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.side_effect = ConnectionError("Host is down")
            assert client.reboot() is False

    def test_reboot_returns_false_on_timeout(self, client):
        """Timeout during reboot returns False (device may already be rebooting)."""
        client._ip = "192.168.0.193"
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.side_effect = ReadTimeout("Read timed out")
            assert client.reboot() is False

    def test_reboot_sends_correct_command(self, client):
        """Reboot sends Device/SysReboot to http://{ip}/post."""
        client._ip = "192.168.0.193"
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            client.reboot()
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "192.168.0.193" in call_args[0][0]
            payload = call_args[0][1]
            assert "Device/SysReboot" in payload
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pixoo_client.py::TestReboot -v`
Expected: FAIL — `PixooClient` has no `reboot()` method

**Step 3: Write minimal implementation**

First, add `import json` to the top of `src/device/pixoo_client.py` (after the existing imports).

Then store the IP in `__init__` — add `self._ip = ip` after `self._error_until = 0.0` (line 102).

Then add after the `ping()` method:

```python
    def reboot(self) -> bool:
        """Send Device/SysReboot command to force the device to restart.

        Best-effort: the device may not respond if it's truly offline,
        or may disconnect mid-reboot. Either case returns False.

        Returns:
            True if the reboot command was acknowledged, False otherwise.
        """
        try:
            _requests_module.post(
                f"http://{self._ip}/post",
                json.dumps({"Command": "Device/SysReboot"}),
            )
            logger.warning("Device reboot command sent to %s", self._ip)
            return True
        except (RequestException, OSError) as exc:
            logger.warning("Device reboot failed: %s", exc)
            return False
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pixoo_client.py::TestReboot -v`
Expected: PASS (4/4)

**Step 5: Update the test fixture**

The existing `client` fixture (line 17-26) doesn't set `_ip`. Update it to include `c._ip = "192.168.0.193"` so existing tests don't break if they ever access `_ip`.

**Step 6: Run full test suite**

Run: `python -m pytest tests/test_pixoo_client.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/device/pixoo_client.py tests/test_pixoo_client.py
git commit -m "feat: add reboot() method to PixooClient for auto-recovery"
```

---

### Task 3: Integrate keep-alive ping into main loop

**Files:**
- Modify: `src/main.py:116-338`
- Test: `tests/test_main_loop.py` (check if this exists first; if not, test manually)

**Step 1: Add constants to main.py**

Add after the imports (after line 51):

```python
# Keep-alive: ping device every 30s to prevent WiFi power-save disconnection
_PING_INTERVAL = 30  # seconds between keep-alive pings
_REBOOT_THRESHOLD = 5  # consecutive device failures before attempting reboot
_REBOOT_RECOVERY_WAIT = 30  # seconds to wait after reboot for device to reconnect
```

**Step 2: Add tracking variables in main_loop**

Add after `needs_push = False` (line 167):

```python
    # Device keep-alive tracking
    last_device_success: float = 0.0  # monotonic time of last successful push or ping
    consecutive_device_failures: int = 0
    reboot_wait_until: float = 0.0  # monotonic time when reboot recovery wait ends
```

**Step 3: Update frame push result handling to track device health**

Modify the existing push result handling block (lines 322-333) to also update keep-alive tracking:

Replace:
```python
            push_result = client.push_frame(frame)
            if push_result is True:
                if health_tracker:
                    health_tracker.record_success("device")
                if state_changed:
                    logger.info("Pushed frame: %s %s", current_state.time_str, current_state.date_str)
            elif push_result is False:
                # Communication error occurred (not just skipped by rate limit/cooldown)
                if health_tracker:
                    health_tracker.record_failure("device", "Device unreachable")
            # push_result is None means skipped (rate limit / cooldown) -- no health action
            needs_push = False
```

With:
```python
            push_result = client.push_frame(frame)
            if push_result is True:
                last_device_success = time.monotonic()
                consecutive_device_failures = 0
                if health_tracker:
                    health_tracker.record_success("device")
                if state_changed:
                    logger.info("Pushed frame: %s %s", current_state.time_str, current_state.date_str)
            elif push_result is False:
                consecutive_device_failures += 1
                if health_tracker:
                    health_tracker.record_failure("device", "Device unreachable")
            # push_result is None means skipped (rate limit / cooldown) -- no health action
            needs_push = False
```

**Step 4: Add keep-alive ping + reboot recovery block**

Add this BEFORE the `time.sleep(1.0)` line (line 338), after the push block:

```python
        # --- Device keep-alive ping + auto-reboot recovery ---
        if now_mono > reboot_wait_until:
            # Check if we should attempt a reboot
            if consecutive_device_failures >= _REBOOT_THRESHOLD:
                logger.warning(
                    "Device has %d consecutive failures, attempting reboot",
                    consecutive_device_failures,
                )
                if client.reboot():
                    reboot_wait_until = time.monotonic() + _REBOOT_RECOVERY_WAIT
                    logger.info("Waiting %ds for device to recover after reboot", _REBOOT_RECOVERY_WAIT)
                else:
                    logger.warning("Reboot command failed (device may be fully offline)")
                consecutive_device_failures = 0  # reset to avoid reboot spam

            # Keep-alive ping when no recent device success
            elif (now_mono - last_device_success) >= _PING_INTERVAL and last_device_success > 0:
                ping_result = client.ping()
                if ping_result is True:
                    last_device_success = time.monotonic()
                    consecutive_device_failures = 0
                    if health_tracker:
                        health_tracker.record_success("device")
                elif ping_result is False:
                    consecutive_device_failures += 1
                    if health_tracker:
                        health_tracker.record_failure("device", "Device ping failed")
```

**Step 5: Verify manually**

Run: `python -m pytest tests/ -v --timeout=30`
Expected: All existing tests pass, no regressions

**Step 6: Commit**

```bash
git add src/main.py
git commit -m "feat: integrate device keep-alive ping and auto-reboot recovery"
```

---

### Task 4: Add main loop keep-alive tests

**Files:**
- Check: `tests/test_main_loop.py` or `tests/test_main.py` — verify if main_loop tests exist
- Create if needed: `tests/test_keepalive.py`

**Step 1: Write integration-level tests for the keep-alive behavior**

Create `tests/test_keepalive.py`:

```python
"""Tests for device keep-alive ping and auto-reboot recovery.

Verifies that the PixooClient ping() and reboot() methods integrate
correctly with the main loop's health tracking.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from requests.exceptions import ConnectionError, ReadTimeout

from src.device.pixoo_client import PixooClient


@pytest.fixture
def client():
    """Create a PixooClient with a mocked Pixoo instance."""
    with patch("src.device.pixoo_client.PixooClient.__init__", lambda self, *a, **kw: None):
        c = object.__new__(PixooClient)
        c._pixoo = MagicMock()
        c._size = 64
        c._last_push_time = 0.0
        c._error_until = 0.0
        c._ip = "192.168.0.193"
        return c


class TestKeepAliveIntegration:
    """Verify ping and push interact correctly with shared state."""

    def test_ping_success_does_not_affect_push_timing(self, client):
        """A successful ping should not reset the push rate limiter."""
        client._last_push_time = time.monotonic()  # recent push
        client._pixoo.validate_connection.return_value = True

        client.ping()

        # _last_push_time should be unchanged (ping doesn't touch it)
        assert client._last_push_time > 0

    def test_ping_failure_sets_cooldown_shared_with_push(self, client):
        """Ping failure cooldown should also block push_frame."""
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        client.ping()

        # Cooldown should now be active
        assert client._error_until > time.monotonic()

        # push_frame should be skipped during cooldown
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        result = client.push_frame(img)
        assert result is None  # skipped due to cooldown

    def test_push_failure_cooldown_blocks_ping(self, client):
        """Push failure cooldown should also block ping."""
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        client._pixoo.push.side_effect = ConnectionError("refused")
        client.push_frame(img)

        # Cooldown should now be active
        result = client.ping()
        assert result is None  # skipped due to cooldown

    def test_reboot_after_multiple_ping_failures(self, client):
        """After multiple ping failures, reboot should still be callable."""
        # Simulate 5 ping failures
        client._pixoo.validate_connection.side_effect = ConnectionError("refused")
        for _ in range(5):
            client._error_until = 0.0  # clear cooldown for each attempt
            client.ping()

        # Reboot should work (separate code path)
        with patch("src.device.pixoo_client._requests_module.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert client.reboot() is True
```

**Step 2: Run tests**

Run: `python -m pytest tests/test_keepalive.py -v`
Expected: PASS (4/4)

**Step 3: Run full suite**

Run: `python -m pytest tests/ -v --timeout=30`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/test_keepalive.py
git commit -m "test: add keep-alive integration tests for ping/reboot/push interaction"
```

---

### Task 5: Final verification and log output review

**Step 1: Run full test suite one final time**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Review log output expectations**

Verify that the new log messages are clear. Expected log behavior during normal operation:
- No new log messages (pings are silent on success)
- On ping failure: `WARNING Device ping failed: <error>`
- On reboot trigger: `WARNING Device has N consecutive failures, attempting reboot`
- On reboot success: `INFO Waiting 30s for device to recover after reboot`
- On reboot failure: `WARNING Reboot command failed (device may be fully offline)`

**Step 3: Commit all together if any loose changes**

```bash
git add -A
git commit -m "feat: device keep-alive ping + auto-reboot recovery

Sends Channel/GetAllConf every 30s to keep ESP32 WiFi radio awake.
After 5 consecutive failures, attempts Device/SysReboot.
Discord alerts fire via existing health tracker integration."
```
