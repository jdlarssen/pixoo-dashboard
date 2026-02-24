# Phase 11: Discord Status Logging for Remote Monitoring - Research

**Researched:** 2026-02-24
**Domain:** Discord bot monitoring, async-to-sync bridging, alert debouncing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Problem alerting only -- silent when healthy
- Startup and shutdown lifecycle messages
- Recovery messages when problems clear (e.g., "Weather API recovered after 23 minutes") with downtime duration
- No periodic heartbeats -- silence means healthy
- Rich Discord embeds with color-coding (red = error, green = recovery, blue = startup/info)
- Detail level: Claude's discretion, but errors should include enough context for `/gsd:debug` sessions -- component, error type, duration, last success time
- Startup embed includes config summary (Pixoo IP, bus stop IDs, weather location)
- Recovery embeds include downtime duration
- Separate dedicated monitoring channel (configured via `DISCORD_MONITOR_CHANNEL_ID` in .env)
- Existing display-message channel completely untouched
- On-demand `status` command in monitoring channel returns a health snapshot
- Optional via `DISCORD_MONITOR_CHANNEL_ID` env var -- no channel configured = no monitoring, zero overhead
- Channel ID is sensitive -- .env only, never committed

### Claude's Discretion
- Which specific errors are alert-worthy vs. ignorable
- Debounce thresholds and repeat-suppression intervals per error type
- On-demand status response content (based on available runtime data)
- Error embed detail level (enough for debugging sessions)
- Repeat-suppression reminder intervals

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Summary

This phase adds a monitoring overlay to the existing Discord bot, sending rich embeds to a separate monitoring channel when problems occur. The project already has a working discord.py 2.6.4 bot running in a daemon thread (`src/providers/discord_bot.py`) that communicates with the main loop via a thread-safe `MessageBridge`. The monitoring system needs to work in the reverse direction: the synchronous main loop must send alerts *to* Discord when it detects failures (bus API down, weather API down, device communication errors).

The key technical challenge is the sync-to-async bridge. The main loop is synchronous (runs in the main thread with `time.sleep(1.0)` ticks), while discord.py's `channel.send()` is async. The established pattern for this is `asyncio.run_coroutine_threadsafe(coro, client.loop)`, which safely schedules an async operation on the Discord bot's event loop from any thread. The existing `client` instance already runs in a daemon thread with its own event loop -- we need to expose that loop reference and provide a thread-safe `send_embed()` method.

**Primary recommendation:** Extend the existing Discord bot module with a `MonitorBridge` class that exposes a synchronous `send_alert(embed)` method backed by `asyncio.run_coroutine_threadsafe()`. Add a `HealthTracker` class to the main loop that tracks component failure/recovery state and debounces alerts. Keep the existing `MessageBridge` and display-message channel completely untouched.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Bot framework, embed creation, channel messaging | Already installed and in use; `discord.Embed` is the native embed API |
| asyncio | stdlib | `run_coroutine_threadsafe()` for sync-to-async bridge | Official Python pattern for cross-thread async calls |
| threading | stdlib | Lock for thread-safe state tracking | Already used by `MessageBridge`; same pattern extends naturally |
| time | stdlib | `monotonic()` for debounce/cooldown timers | Already used throughout `main.py` and `pixoo_client.py` |
| datetime | stdlib | Timestamps for embeds and downtime duration calculation | Already used in main loop |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging | stdlib | Log monitoring events locally alongside Discord alerts | Every alert should also be logged locally |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Embed via bot client | Discord webhooks (SyncWebhook) | Simpler sync API but requires separate webhook URL config; bot client is already running and can also listen for `status` command |
| Single bot, two channels | Separate bot instances | Wasteful -- one bot token can listen/send to multiple channels; Discord rate limits are per-route anyway |

**Installation:**
No new packages needed. discord.py 2.6.4 already installed. All other dependencies are stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── providers/
│   ├── discord_bot.py     # EXISTING: MessageBridge, run_discord_bot, start_discord_bot
│   └── discord_monitor.py # NEW: MonitorBridge, HealthTracker, alert/recovery logic
├── config.py              # ADD: DISCORD_MONITOR_CHANNEL_ID env var
└── main.py                # MODIFY: integrate HealthTracker into main loop
```

### Pattern 1: Sync-to-Async Bridge via asyncio.run_coroutine_threadsafe
**What:** The main loop (sync) needs to send Discord embeds (async). Use `asyncio.run_coroutine_threadsafe()` to schedule coroutines on the bot's event loop from the main thread.
**When to use:** Every time the main loop wants to send an alert, recovery, or status embed.
**Example:**
```python
# Source: discord.py FAQ - https://discordpy.readthedocs.io/en/stable/faq.html
import asyncio
import discord

class MonitorBridge:
    """Thread-safe bridge for sending monitoring embeds from sync main loop."""

    def __init__(self, client: discord.Client, channel_id: int):
        self._client = client
        self._channel_id = channel_id
        self._loop = client.loop  # captured after client.run() starts

    def send_embed(self, embed: discord.Embed) -> None:
        """Send an embed to the monitoring channel (thread-safe, non-blocking)."""
        channel = self._client.get_channel(self._channel_id)
        if channel is None:
            return
        coro = channel.send(embed=embed)
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            fut.result(timeout=5.0)  # wait up to 5s for delivery
        except Exception:
            pass  # log but don't crash the main loop
```

### Pattern 2: Health State Tracker with Debounced Alerting
**What:** Track per-component failure state (first_failure_time, last_alert_time, failure_count, is_alerting) and only emit alerts after a debounce window. Emit recovery embeds when a previously-failed component succeeds.
**When to use:** In the main loop, after each data fetch attempt.
**Example:**
```python
import time
from dataclasses import dataclass, field

@dataclass
class ComponentState:
    """Tracks health state for one monitored component."""
    name: str
    first_failure_time: float = 0.0      # monotonic time of first consecutive failure
    last_alert_time: float = 0.0         # monotonic time of last alert sent
    failure_count: int = 0               # consecutive failures
    is_alerting: bool = False            # whether we've sent an alert for current failure
    last_success_time: float = 0.0       # monotonic time of last successful operation

class HealthTracker:
    """Tracks component health and emits debounced alerts."""

    def __init__(self, monitor: MonitorBridge | None):
        self._monitor = monitor
        self._components: dict[str, ComponentState] = {}

    def record_success(self, component: str) -> None:
        """Record a successful operation. Emits recovery if was alerting."""
        state = self._components.get(component)
        if state and state.is_alerting:
            # Emit recovery embed with downtime duration
            downtime = time.monotonic() - state.first_failure_time
            self._send_recovery(state, downtime)
        if state:
            state.failure_count = 0
            state.is_alerting = False
            state.first_failure_time = 0.0
            state.last_success_time = time.monotonic()

    def record_failure(self, component: str, error_info: str) -> None:
        """Record a failed operation. Debounces before alerting."""
        state = self._components.setdefault(component, ComponentState(name=component))
        now = time.monotonic()
        if state.failure_count == 0:
            state.first_failure_time = now
        state.failure_count += 1
        # Debounce: only alert after threshold consecutive failures
        # ...
```

### Pattern 3: Reuse Existing Bot Client for Both Channels
**What:** The existing `run_discord_bot()` creates a `discord.Client` that listens on the display-message channel. Extend it to also listen for `status` commands on the monitoring channel, and expose the client + loop for the `MonitorBridge`.
**When to use:** At startup, when configuring the bot.
**Example:**
```python
# Extended on_message handler -- check BOTH channel IDs
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Display message channel (existing behavior)
    if message.channel.id == display_channel_id:
        # ... existing message bridge logic ...
        pass

    # Monitoring channel (new)
    if message.channel.id == monitor_channel_id:
        if message.content.strip().lower() == "status":
            embed = build_status_embed(health_tracker)
            await message.channel.send(embed=embed)
            await message.add_reaction("\u2713")
```

### Pattern 4: Color-Coded Embeds
**What:** Use Discord embed colors to visually distinguish alert types at a glance.
**When to use:** Every monitoring embed.
**Example:**
```python
# Source: discord.py Embed API
import discord
from datetime import datetime, timezone

def error_embed(component: str, error_type: str, detail: str,
                duration_s: float, last_success: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Error: {component}",
        description=detail,
        color=0xFF0000,  # Red
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Component", value=component, inline=True)
    embed.add_field(name="Error Type", value=error_type, inline=True)
    embed.add_field(name="Failing For", value=f"{duration_s:.0f}s", inline=True)
    embed.add_field(name="Last Success", value=last_success, inline=True)
    embed.set_footer(text="Divoom Hub Monitor")
    return embed

def recovery_embed(component: str, downtime_s: float) -> discord.Embed:
    minutes = downtime_s / 60
    embed = discord.Embed(
        title=f"Recovered: {component}",
        description=f"{component} recovered after {minutes:.0f} minutes",
        color=0x00FF00,  # Green
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Divoom Hub Monitor")
    return embed

def startup_embed(config: dict) -> discord.Embed:
    embed = discord.Embed(
        title="Divoom Hub Started",
        description="Dashboard is online",
        color=0x3498DB,  # Blue
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Pixoo IP", value=config["ip"], inline=True)
    embed.add_field(name="Weather", value=f"{config['lat']}, {config['lon']}", inline=True)
    embed.set_footer(text="Divoom Hub Monitor")
    return embed
```

### Anti-Patterns to Avoid
- **Running a second discord.Client:** One bot token = one client. Running multiple clients with the same token causes gateway conflicts. Reuse the existing client instance.
- **Blocking the main loop on Discord sends:** Use `fut.result(timeout=5.0)` with a short timeout, or make sends fire-and-forget. Never let a Discord API failure block the 1-second render loop.
- **Alerting on first failure:** Transient blips are normal (network hiccup, API momentary 503). Always debounce with 2-3 consecutive failures before alerting.
- **Spamming the channel:** Without repeat suppression, a down API could generate an alert every 60 seconds forever. Implement exponential backoff on repeat alerts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rich formatted messages | Custom text formatting | `discord.Embed` with fields, colors, timestamps | Native Discord rendering, mobile-friendly, color-coded |
| Sync-to-async calls | Custom thread/queue system | `asyncio.run_coroutine_threadsafe()` | Python stdlib, battle-tested, exactly designed for this case |
| Rate limiting | Manual rate limit tracking | discord.py's built-in rate limit handler | The library automatically retries on 429s with proper backoff |
| Timestamp formatting | Manual UTC string formatting | `discord.Embed(timestamp=datetime.now(timezone.utc))` | Discord renders it in the user's local timezone automatically |

**Key insight:** discord.py already handles rate limits, retries, and websocket reconnection. The monitoring layer should focus on *what* to alert and *when*, not on Discord API mechanics.

## Common Pitfalls

### Pitfall 1: Client.loop Not Available Until on_ready
**What goes wrong:** Accessing `client.loop` before the bot connects raises an error or returns None.
**Why it happens:** The event loop is set up during `client.run()`, which happens in the daemon thread.
**How to avoid:** Use an `asyncio.Event` or callback in `on_ready` to signal that the bot is ready and the loop is available. Only then create the `MonitorBridge`.
**Warning signs:** `AttributeError` on loop access, or monitoring silently failing on startup.

### Pitfall 2: get_channel Returns None
**What goes wrong:** `client.get_channel(id)` returns `None` if the bot hasn't cached that channel yet, or if the bot doesn't have access.
**Why it happens:** Channel cache is populated by the GUILD_CREATE event during connection. If the channel ID is wrong or the bot lacks permissions, it's not cached.
**How to avoid:** Check for `None` before sending. Log a clear warning at startup if the monitoring channel can't be found. Alternatively, use `await client.fetch_channel(id)` which makes an API call (slower but reliable).
**Warning signs:** Alerts silently not being delivered; no error because `None` check just returns.

### Pitfall 3: Blocking the Main Loop on Discord Sends
**What goes wrong:** `fut.result()` without a timeout blocks indefinitely if Discord is unreachable.
**Why it happens:** The main loop calls `send_embed()` synchronously, waiting for the Discord API response.
**How to avoid:** Always use `fut.result(timeout=5.0)` or make sends fire-and-forget (don't call `result()` at all). Catch `TimeoutError` and `Exception` silently.
**Warning signs:** Display freezes; the 1-second render loop stalls.

### Pitfall 4: Alert Storm on Extended Outage
**What goes wrong:** If the bus API is down for hours, the bot sends an alert every 60 seconds (every bus refresh cycle).
**Why it happens:** No repeat suppression -- each failure triggers a new alert.
**How to avoid:** Track `is_alerting` state per component. After the initial alert, only send reminders at increasing intervals (e.g., 5min, 15min, 1hr). Or just send one alert and one recovery.
**Warning signs:** Monitoring channel flooded with identical error messages.

### Pitfall 5: Monitoring Failures Crashing the Main Loop
**What goes wrong:** An unhandled exception in the monitoring code (e.g., Discord API error) propagates up and crashes the dashboard.
**Why it happens:** The monitoring system is additive -- it should never affect core display functionality.
**How to avoid:** Wrap ALL monitoring calls in try/except. Every `send_embed()` call should be wrapped. Use the same defensive pattern as the existing `fetch_weather_safe()`.
**Warning signs:** Dashboard crashes with Discord-related tracebacks.

### Pitfall 6: Startup Race Condition
**What goes wrong:** The main loop starts and immediately tries to send a startup embed before the Discord bot has connected.
**Why it happens:** `start_discord_bot()` returns immediately (it spawns a daemon thread), but the bot takes 1-3 seconds to connect to Discord's gateway.
**How to avoid:** Either wait for `on_ready` before sending the startup embed, or queue the startup embed and send it when the bot signals ready.
**Warning signs:** Startup embed never arrives, or `get_channel()` returns None.

## Code Examples

### Discord Embed Color Constants
```python
# Source: discord.py Embed API documentation
COLORS = {
    "error": 0xFF0000,       # Red -- problems
    "recovery": 0x00FF00,    # Green -- recovery
    "startup": 0x3498DB,     # Blue -- lifecycle info
    "shutdown": 0x95A5A6,    # Gray -- lifecycle info
    "warning": 0xFFA500,     # Orange -- degraded but not failed (optional)
}
```

### Debounce Configuration (Recommended Thresholds)
```python
# Debounce thresholds per component
DEBOUNCE_CONFIG = {
    "bus_api": {
        "failures_before_alert": 3,      # 3 consecutive failures (3 minutes at 60s refresh)
        "repeat_interval": 900,           # 15 minutes between repeat alerts
    },
    "weather_api": {
        "failures_before_alert": 2,       # 2 consecutive failures (20 minutes at 600s refresh)
        "repeat_interval": 1800,          # 30 minutes between repeat alerts
    },
    "device": {
        "failures_before_alert": 5,       # 5 consecutive failures (5 seconds at 1s push)
        "repeat_interval": 300,           # 5 minutes between repeat alerts
    },
}
```

### Thread-Safe Send Pattern (Complete)
```python
# Source: discord.py FAQ - asyncio.run_coroutine_threadsafe
import asyncio
import logging
import discord

logger = logging.getLogger(__name__)

class MonitorBridge:
    def __init__(self, client: discord.Client, channel_id: int):
        self._client = client
        self._channel_id = channel_id

    def send_embed(self, embed: discord.Embed) -> bool:
        """Send embed to monitoring channel. Returns True on success."""
        try:
            channel = self._client.get_channel(self._channel_id)
            if channel is None:
                logger.warning("Monitor channel %d not found in cache", self._channel_id)
                return False
            coro = channel.send(embed=embed)
            fut = asyncio.run_coroutine_threadsafe(coro, self._client.loop)
            fut.result(timeout=5.0)
            return True
        except Exception:
            logger.exception("Failed to send monitoring embed")
            return False
```

### On-Demand Status Command Response
```python
# Example status embed with runtime health data
def build_status_embed(tracker: HealthTracker, uptime_s: float) -> discord.Embed:
    embed = discord.Embed(
        title="Divoom Hub Status",
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc),
    )
    hours = int(uptime_s // 3600)
    mins = int((uptime_s % 3600) // 60)
    embed.add_field(name="Uptime", value=f"{hours}h {mins}m", inline=True)

    for name, state in tracker.components.items():
        if state.is_alerting:
            dur = time.monotonic() - state.first_failure_time
            embed.add_field(name=name, value=f"DOWN ({dur:.0f}s)", inline=True)
        else:
            embed.add_field(name=name, value="OK", inline=True)

    embed.set_footer(text="Divoom Hub Monitor")
    return embed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| discord.py Webhook (sync) | discord.py Client + asyncio.run_coroutine_threadsafe | discord.py 2.0 (2022) | Reusing existing Client is simpler than managing a separate Webhook URL |
| Plain text messages | discord.Embed with fields and colors | Long-standing | Structured, color-coded, mobile-friendly rendering |
| No rate limit handling | Built-in in discord.py 2.x | discord.py 2.0+ | Library handles 429 retries automatically |

**Deprecated/outdated:**
- `discord.py v1.x` loop patterns: In v1.x, `client.loop` was more reliably available. In v2.x, the loop is created lazily. Use `asyncio.get_event_loop()` from within the bot's thread, or capture it in `on_ready`.

## Open Questions

1. **Fire-and-forget vs. blocking sends?**
   - What we know: `fut.result(timeout=5.0)` blocks up to 5 seconds per alert. Most sends complete in <100ms.
   - What's unclear: Whether 5s timeout is acceptable if Discord has a transient issue during a render loop tick.
   - Recommendation: Use fire-and-forget (skip `fut.result()`) for error alerts from the main loop. The main loop's 1-second cadence is more important than confirming alert delivery. Log send failures locally.

2. **Should shutdown embed be sent?**
   - What we know: User wants startup and shutdown lifecycle messages. But on `KeyboardInterrupt`, the daemon thread (Discord bot) dies immediately.
   - What's unclear: Whether there's enough time to send a shutdown embed before process exit.
   - Recommendation: Attempt it with a very short timeout (1-2 seconds) in a `finally` block. Accept that forced kills (SIGKILL, OOM) won't produce a shutdown embed. This is fine -- the *absence* of a startup embed after expected uptime signals a problem.

3. **Device communication errors -- alert-worthy?**
   - What we know: `PixooClient.push_frame()` already catches `RequestException` and `OSError`, logs a warning, and applies a 3-second cooldown. Device issues are usually transient (WiFi hiccup).
   - What's unclear: Whether device errors should be reported to Discord or just logged locally.
   - Recommendation: Only alert on sustained device failures (5+ consecutive errors spanning >30 seconds). Device blips are too frequent and self-healing to warrant Discord alerts.

## Sources

### Primary (HIGH confidence)
- discord.py 2.6.4 installed in project (verified via `pip show`)
- [discord.py FAQ - asyncio.run_coroutine_threadsafe pattern](https://discordpy.readthedocs.io/en/stable/faq.html)
- Existing codebase: `src/providers/discord_bot.py`, `src/main.py`, `src/config.py`
- [Discord API Rate Limits](https://docs.discord.com/developers/topics/rate-limits) -- 50 req/sec global limit

### Secondary (MEDIUM confidence)
- [Discord Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/) -- 256 char title, 4096 char desc, 25 fields, 6000 total
- [discord.py Masterclass - Embeds](https://fallendeity.github.io/discord.py-masterclass/embeds/) -- Embed creation patterns
- [discord.py GitHub Discussion #5868](https://github.com/Rapptz/discord.py/discussions/5868) -- Sending from another thread

### Tertiary (LOW confidence)
- Debounce thresholds: Recommended values are based on the project's existing refresh intervals (60s bus, 600s weather) -- need tuning based on real-world noise levels.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- discord.py 2.6.4 already installed and working; all patterns use stdlib
- Architecture: HIGH -- sync-to-async bridge is well-documented discord.py pattern; codebase structure is clear
- Pitfalls: HIGH -- identified from codebase analysis (existing thread model, error handling patterns) and discord.py docs
- Debounce thresholds: MEDIUM -- reasonable starting values but may need tuning

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable domain, discord.py 2.x is mature)
