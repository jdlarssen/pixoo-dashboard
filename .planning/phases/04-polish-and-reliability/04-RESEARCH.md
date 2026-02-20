# Phase 4: Polish and Reliability - Research

**Researched:** 2026-02-20
**Domain:** Production hardening (brightness, urgency colors, error handling, service supervision, Discord messaging, visual polish)
**Confidence:** HIGH

## Summary

Phase 4 transforms the working dashboard into a production-quality daily-use appliance. The six areas -- urgency coloring, auto-brightness, error/staleness handling, service supervision, Discord message override, and visual color pass -- are largely independent features that modify or extend existing code rather than introducing new architectural patterns.

The most significant new dependency is **discord.py** for the message override feature. Discord.py requires an asyncio event loop, but the current main loop is synchronous (`time.sleep`-based). The recommended integration pattern is to run the Discord bot in a background thread with its own asyncio event loop, using a thread-safe shared variable to pass messages to the synchronous main loop.

The remaining features (brightness scheduling, urgency colors, staleness tracking, launchd service wrapper) require no new dependencies and build directly on the existing PIL rendering and `pixoo` library capabilities.

**Primary recommendation:** Implement features in waves -- infrastructure/data-model changes first (brightness, urgency colors, staleness), then Discord integration and visual polish, and finally the service wrapper and birthday easter egg.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Urgency color thresholds: Green (>10 min), Yellow (5-10 min), Red (<5 min), Dimmed/grey (<2 min)
- Color applied to departure countdown text only (not backgrounds)
- Brightness dim mode: 21:00 to 06:00
- Night brightness: 15-25% range
- Day brightness: full (100%)
- Error handling: show last known data with staleness indicator when API fails
- When data is too old: display dash placeholders ("--" or "- min"), not blank
- Messages via Discord bot (not terminal/CLI)
- Messages are persistent reminders, not flash notifications
- Messages stay until explicitly cleared or replaced
- Display placement: message alongside existing dashboard (bottom-right, next to weather) -- fallback to full-screen override if space doesn't permit
- The entire display needs a color overhaul -- too grey and monochrome
- Clock is too large, needs to shrink and rebalance zones
- Weather animations need vivid color (rain, sun, etc. currently grey/boring)
- Birthday easter egg: March 17 and December 16 with crown/festive icon and additional festive touches

### Claude's Discretion
- Transition style for brightness changes
- Config vs hardcoded for brightness schedule
- Staleness indicator visual approach
- Staleness timeout thresholds per data type
- Clock error detection (likely skip)
- Zone rebalancing after clock resize
- Color palette design for the whole display
- Zone separator approach
- Date and label color treatments
- Weather animation color palette
- Birthday easter egg full design
- Direction labels urgency color inheritance

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISP-04 | Auto-brightness based on time of day | Pixoo `set_brightness` API accepts 0-100, capped at 90% by existing PixooClient. Schedule-driven brightness changes via datetime checks in main loop. |
| BUS-04 | Color coding by urgency (green/yellow/red) | Pure rendering change in renderer.py `_draw_bus_line` -- color selection based on departure minutes value. No new dependencies. |
| RLBL-02 | Graceful error states (show last known data when API fails) | Staleness tracking via monotonic timestamps in main loop. Existing `_safe` wrappers return None on failure; extend to preserve last-good data and track age. |
| RLBL-03 | Auto-restart via service wrapper (systemd/launchd) | macOS launchd plist with KeepAlive for auto-restart on crash. Standard pattern, no code dependency. |
| MSG-01 | Push text message to temporarily override display | discord.py bot in background thread, shared message state via threading.Event or simple lock-protected variable. Renderer checks message state each frame. |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pixoo | 0.9.2 | Pixoo 64 device communication | Already in use, provides `set_brightness(0-100)` via HTTP POST to device |
| Pillow (PIL) | installed | Image rendering | Already in use for all frame rendering |
| requests | installed | HTTP API calls | Already in use for bus and weather APIs |

### New Dependencies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.x (latest stable) | Discord bot for message override | De facto standard Python Discord library. 73M+ downloads on PyPI. Supports intents, `on_message` events, async/await. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| discord.py | Discord webhooks (requests only) | Webhooks are send-only; cannot RECEIVE messages from Discord channels. Bot is required for bidirectional communication. |
| discord.py | Lightweight HTTP polling of Discord API | Would require raw REST calls, manual rate limiting, no WebSocket events. discord.py handles all of this. |
| launchd plist | supervisord / systemd | This is macOS -- launchd is the native supervisor. systemd is Linux-only. supervisord adds a dependency. |

### Installation
```bash
pip install discord.py
```

No other new dependencies needed.

## Architecture Patterns

### Recommended Integration: Discord Bot in Background Thread

The current `main.py` runs a synchronous `while True` loop with `time.sleep()`. discord.py requires an asyncio event loop. The cleanest integration:

```
Main Thread (synchronous)          Background Thread (asyncio)
┌──────────────────────┐          ┌──────────────────────┐
│ while True:          │          │ discord.Client.run() │
│   check brightness   │  shared  │   on_message:        │
│   fetch bus/weather   │◄────────│     set message_text │
│   check message_state │  var    │     set clear flag   │
│   render_frame()     │          │                      │
│   push to device     │          │                      │
│   sleep              │          │                      │
└──────────────────────┘          └──────────────────────┘
```

**Pattern:** Run `discord.Client` in a daemon thread via `threading.Thread(target=..., daemon=True)`. Use a thread-safe shared object (e.g., `threading.Lock`-protected dataclass or simple `queue.Queue`) for the main loop to read the current message.

**Code sketch:**
```python
import threading
import discord

class MessageBridge:
    """Thread-safe bridge between Discord bot and main loop."""
    def __init__(self):
        self._lock = threading.Lock()
        self._message: str | None = None

    def set_message(self, text: str | None):
        with self._lock:
            self._message = text

    @property
    def current_message(self) -> str | None:
        with self._lock:
            return self._message

def run_discord_bot(bridge: MessageBridge, token: str, channel_id: int):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_message(message):
        if message.channel.id != channel_id:
            return
        if message.author == client.user:
            return
        content = message.content.strip()
        if content.lower() in ("clear", "cls", "reset"):
            bridge.set_message(None)
        else:
            bridge.set_message(content)

    client.run(token)

# In main():
bridge = MessageBridge()
bot_thread = threading.Thread(
    target=run_discord_bot,
    args=(bridge, DISCORD_TOKEN, DISCORD_CHANNEL_ID),
    daemon=True,
)
bot_thread.start()
```

### Brightness Scheduling Pattern

```python
from datetime import datetime

def get_target_brightness(now: datetime) -> int:
    """Return target brightness based on time of day."""
    hour = now.hour
    if 21 <= hour or hour < 6:  # 21:00 - 06:00
        return 20  # Night mode (15-25 range)
    return 100  # Day mode (will be capped to 90 by PixooClient)
```

Call `client.set_brightness(get_target_brightness(now))` in the main loop. The existing `PixooClient.set_brightness()` already caps at `MAX_BRIGHTNESS` (90%). No gradual ramp needed for a 64x64 LED -- step change is fine; the device transitions smoothly internally.

### Urgency Color Selection Pattern

```python
def urgency_color(minutes: int) -> tuple[int, int, int]:
    """Return RGB color for bus departure based on urgency."""
    if minutes < 2:
        return (80, 80, 80)     # Dimmed grey -- bus has effectively left
    elif minutes < 5:
        return (255, 50, 50)    # Red -- imminent
    elif minutes <= 10:
        return (255, 200, 0)    # Yellow -- hurry
    else:
        return (50, 255, 50)    # Green -- plenty of time
```

Apply per-departure in `_draw_bus_line` instead of the current `COLOR_BUS_TIME` constant.

### Staleness Tracking Pattern

```python
from dataclasses import dataclass
import time

@dataclass
class StaleData:
    """Wraps data with a freshness timestamp."""
    data: any
    fetched_at: float  # time.monotonic()

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.fetched_at

    def is_stale(self, max_age: float) -> bool:
        return self.age_seconds > max_age
```

**Staleness thresholds (recommended):**
| Data Source | Normal Refresh | Stale After | Too Old (show dashes) |
|-------------|----------------|-------------|------------------------|
| Bus (Entur) | 60s | 180s (3 min) | 600s (10 min) |
| Weather (MET) | 600s (10 min) | 1800s (30 min) | 3600s (1 hour) |

When stale but not too old: show data with a visual indicator (e.g., dim the colors, add a small dot marker).
When too old: show dash placeholders ("--").

### Anti-Patterns to Avoid
- **Don't run discord.py in the main thread:** It will block the rendering loop. Always use a background thread.
- **Don't use webhook-only approach for receiving:** Discord webhooks are send-only. You MUST use a bot with gateway connection to receive messages from a channel.
- **Don't catch-all exceptions silently:** The existing `_safe` wrappers log exceptions. Maintain this pattern for staleness tracking -- log + preserve last-good data.
- **Don't hardcode Discord token in source:** Use environment variable or config file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Discord message receiving | HTTP polling of Discord REST API | discord.py `on_message` event | Rate limits, WebSocket reconnection, intent handling all built-in |
| Service supervision | Custom watchdog script | macOS launchd plist with KeepAlive | OS-native, handles crashes, boot, and user login. Battle-tested. |
| Async/sync bridging | Custom event loop management | `threading.Thread(daemon=True)` + `threading.Lock` | Simple, well-understood, no async contamination of main loop |

**Key insight:** The most complex new integration (Discord bot) has a well-established pattern. The rest of Phase 4 is rendering logic changes and configuration.

## Common Pitfalls

### Pitfall 1: Discord Bot Token Security
**What goes wrong:** Token committed to git or hardcoded in source.
**Why it happens:** Quick development without thinking about deployment.
**How to avoid:** Use `os.environ.get("DISCORD_BOT_TOKEN")` or a config file excluded from git. Add token config to `.env.example` but never `.env` itself.
**Warning signs:** Token string literals in Python source files.

### Pitfall 2: Message Content Intent Not Enabled
**What goes wrong:** Bot connects but `on_message` never fires or `message.content` is empty.
**Why it happens:** Discord requires explicit opt-in to `message_content` intent (since 2022). Must be enabled both in code AND in Discord Developer Portal.
**How to avoid:** Set `intents.message_content = True` in code. Enable "Message Content Intent" in bot settings on Discord Developer Portal.
**Warning signs:** Bot appears online but ignores all messages.

### Pitfall 3: Brightness API Call Rate
**What goes wrong:** Calling `set_brightness()` every loop iteration (every 0.35s when animation active) floods the device with HTTP requests.
**Why it happens:** Brightness check in tight loop without change detection.
**How to avoid:** Track `last_brightness` value, only call `set_brightness()` when the target changes. Check once per minute, not every frame.
**Warning signs:** Increased latency in frame pushing, device becoming unresponsive.

### Pitfall 4: Thread Safety for Message Bridge
**What goes wrong:** Race condition between Discord bot writing message and main loop reading it.
**Why it happens:** String assignment in Python is atomic for simple cases, but compound state (message + timestamp) needs protection.
**How to avoid:** Use `threading.Lock` around all reads and writes to shared message state.
**Warning signs:** Intermittent display of partial/corrupt message text.

### Pitfall 5: Zone Layout Changes Breaking Existing Rendering
**What goes wrong:** Changing clock zone height to free up space causes cascade of y-coordinate mismatches across all zones.
**Why it happens:** Zone positions are interdependent (each starts where the previous ends).
**How to avoid:** Change zone definitions in `layout.py` FIRST, then update all rendering code to use the zone constants (not hardcoded pixel values). Verify with `--simulated --save-frame`.
**Warning signs:** Text/zones overlapping or gaps appearing in the display.

### Pitfall 6: Launchd Environment Variables
**What goes wrong:** Script works in terminal but fails when launched by launchd because environment variables (DISCORD_BOT_TOKEN, DIVOOM_IP, etc.) are not set.
**Why it happens:** launchd runs in a minimal environment without user shell profile.
**How to avoid:** Use `EnvironmentVariables` dict in the plist, or read from a config file / `.env` file instead of relying on shell environment.
**Warning signs:** "None" errors for environment variable values, connection failures.

## Code Examples

### Pixoo Brightness API (from installed library source)
```python
# pixoo library set_brightness implementation (verified from source):
# pixoo/objects/pixoo.py line 380
def set_brightness(self, brightness):
    if self.simulated:
        return
    brightness = clamp(brightness, 0, 100)
    response = requests.post(self.__url, json.dumps({
        'Command': 'Channel/SetBrightness',
        'Brightness': brightness
    }))
```
Source: Installed pixoo 0.9.2 library, `pixoo/objects/pixoo.py`

### discord.py Minimal Bot for Message Receiving
```python
import discord

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id == TARGET_CHANNEL_ID:
        print(f"Message: {message.content}")

client.run("TOKEN")
```
Source: discord.py official quickstart (https://discordpy.readthedocs.io/en/stable/quickstart.html)

### launchd Plist with KeepAlive
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.divoom-hub.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/divoom-hub/src/main.py</string>
        <string>--ip</string>
        <string>192.168.1.100</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/divoom-hub</string>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/divoom-hub.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/divoom-hub.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DIVOOM_IP</key>
        <string>192.168.1.100</string>
        <key>DISCORD_BOT_TOKEN</key>
        <string>YOUR_TOKEN_HERE</string>
        <key>DISCORD_CHANNEL_ID</key>
        <string>YOUR_CHANNEL_ID</string>
    </dict>
</dict>
</plist>
```
Source: macOS launchd documentation pattern (https://www.launchd.info/)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| discord.py sync (0.x) | discord.py async (2.x) with intents | 2022 | Must enable intents explicitly; fully async API |
| Message content default access | Privileged intent required | Sept 2022 | Must opt-in to message_content intent in code AND developer portal |
| systemd for all | launchd for macOS, systemd for Linux | Always | macOS uses launchd natively; systemd not available |

**Deprecated/outdated:**
- discord.py `bot.run()` without intents: Will silently fail to receive message content
- Old `discord.py` rewrite branch: Community fork `pycord` exists but `discord.py` (Rapptz) is maintained again as of 2022

## Open Questions

1. **Discord Bot Token Provisioning**
   - What we know: Need a bot token from Discord Developer Portal and the target channel ID
   - What's unclear: Whether the user has already created a Discord bot application
   - Recommendation: Plan should include instructions for bot creation as a prerequisite step, with token passed via environment variable

2. **Message Display Space on 64x64**
   - What we know: User prefers alongside dashboard (bottom-right). Current weather zone is 20px tall. Messages need readable text.
   - What's unclear: Whether message text can fit alongside weather in remaining space after zone rebalancing
   - Recommendation: Try compact message zone first (e.g., 8-10px at very bottom); fall back to full-screen overlay if text is unreadable at that size

3. **Existing Todo: Weather Animation Colors**
   - What we know: There's a pending todo about rain/snow animation colors being grey and indistinguishable from text
   - What's unclear: Whether this should be addressed in the visual color pass or as a separate fix
   - Recommendation: Fold into the visual color pass plan since the color overhaul is already planned

## Sources

### Primary (HIGH confidence)
- Installed pixoo 0.9.2 library source code -- verified `set_brightness()` accepts 0-100, sends `Channel/SetBrightness` HTTP command
- Existing codebase (`src/`) -- verified architecture, rendering patterns, state model, all provider implementations
- discord.py official docs (https://discordpy.readthedocs.io/en/stable/quickstart.html) -- bot setup, intents, on_message
- macOS launchd documentation (https://www.launchd.info/) -- KeepAlive, plist structure

### Secondary (MEDIUM confidence)
- discord.py threading discussion (https://github.com/Rapptz/discord.py/discussions/9749) -- background thread pattern
- discord.py FAQ (https://discordpy.readthedocs.io/en/stable/faq.html) -- coroutine thread safety

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pixoo API verified from installed source; discord.py is de facto standard
- Architecture: HIGH -- threading pattern well-documented; rendering changes are straightforward PIL modifications
- Pitfalls: HIGH -- common issues documented in discord.py FAQ and GitHub discussions
- Brightness: HIGH -- verified from pixoo library source code
- Urgency colors: HIGH -- pure rendering logic, no external dependency
- Staleness: HIGH -- standard timestamp-based pattern, no external dependency
- Service wrapper: HIGH -- launchd is well-documented macOS standard
- Visual polish: MEDIUM -- color choices are design decisions; LED rendering may need iteration

**Research date:** 2026-02-20
**Valid until:** 2026-03-22 (30 days -- stable domain, no fast-moving dependencies)
