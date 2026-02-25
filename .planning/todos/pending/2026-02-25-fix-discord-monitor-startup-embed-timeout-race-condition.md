---
created: 2026-02-25T21:26:18.599Z
title: Fix Discord monitor startup embed timeout race condition
area: discord
files:
  - src/providers/discord_monitor.py:256-258
  - src/main.py:415-437
---

## Problem

The `on_ready_callback` in `main()` fires and calls `monitor_bridge.send_embed()` to send the startup embed. `send_embed` uses `asyncio.run_coroutine_threadsafe` with a 5-second `fut.result(timeout=5.0)`. This times out with a `TimeoutError` traceback, likely because the Discord gateway isn't fully ready to send messages yet despite `on_ready` having fired.

Despite the exception, the embed appears to get delivered after the timeout — the log line "Monitoring active -- startup embed sent" prints unconditionally after the `send_embed` call because `on_ready_callback` doesn't check the return value.

Observed log output:
```
2026-02-25 22:22:26,479 [src.providers.discord_monitor] Failed to send monitoring embed
Traceback (most recent call last):
  File ".../discord_monitor.py", line 258, in send_embed
    fut.result(timeout=5.0)
TimeoutError
2026-02-25 22:22:26,482 [__main__] Monitoring active -- startup embed sent to channel ...
```

## Solution

TBD — needs investigation via `/gsd:debug`. Possible approaches:
- Add a short delay in `on_ready_callback` before sending the startup embed
- Retry the embed send on timeout
- Check `send_embed` return value in `on_ready_callback` and log accurately
- Increase the future timeout for the startup embed specifically
