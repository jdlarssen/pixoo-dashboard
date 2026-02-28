# Divoom Hub

> Always-on LED dashboard for Pixoo 64 -- clock, bus departures, and weather at a glance.

[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-orange?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/code)

<!-- Replace the image below with a real photo of your display.
     Place the image at docs/display-photo.jpg (or update the path). -->
<!-- ![Pixoo 64 dashboard in action](docs/display-photo.jpg) -->

A personal home dashboard running on a Divoom Pixoo 64 LED display. A quick glance shows you the time, when the next bus leaves, and the current weather -- without picking up your phone.

Built as a hobby project for personal use. The display sits on a shelf showing real-time data 24/7: clock with Norwegian date formatting, bus departures from two directions with color-coded countdowns (green, yellow, red), weather with animated overlays (rain, snow, sun, thunder, fog), and an optional Discord message feature for pushing short messages to the screen.

Written entirely in Python, communicating with the Pixoo 64 over LAN. Weather data comes from MET Norway (yr.no backend), bus data from Entur, and the clock is formatted in Norwegian with special characters.

---

## Display Layout (64x64 pixels)

The display is divided into six zones filling the entire 64x64 screen:

```
+----------------------------------------------------------------+
|  14:32  [sun]                                           CLOCK   |  y 0-10
|  tor 20. feb                                             DATE   |  y 11-18
|----------------------------------------------------------------|  y 19
|  <S  5  12  25                                            BUS   |  y 20-29
|  >L  3   8  18                                            BUS   |  y 30-38
|----------------------------------------------------------------|  y 39
|  7   2.3mm                                            WEATHER   |  y 40-49
|  5/2          ~~~                                               |  y 50-58
|                ~~~                                              |  y 59-63
+----------------------------------------------------------------+
```

| Zone | Y-start | Y-end | Height | Content |
|------|---------|-------|--------|---------|
| Clock | 0 | 10 | 11 px | HH:MM in 24-hour format + weather icon |
| Date | 11 | 18 | 8 px | Norwegian date, e.g. "tor 20. feb" |
| Divider | 19 | 19 | 1 px | Thin teal line |
| Bus | 20 | 38 | 19 px | Two directions with color-coded countdowns |
| Divider | 39 | 39 | 1 px | Thin teal line |
| Weather | 40 | 63 | 24 px | Temperature, high/low, precipitation, animation |

**Bus countdown colors:**
- Green: > 10 min (plenty of time)
- Yellow: 5--10 min (hurry up)
- Red: < 5 min (almost gone)
- Dimmed: < 2 min (effectively departed)

---

## Prerequisites

- **Python 3.10+**
- **Divoom Pixoo 64** on the same local network (LAN)
- Internet connection for weather and bus APIs

Dependencies (installed automatically):

| Package | Version | Purpose |
|---------|---------|---------|
| pixoo | >= 0.5 | Communication with Pixoo 64 |
| Pillow | >= 10.0 | Image processing and font rendering |
| requests | >= 2.28 | HTTP client for API calls and device communication |
| astral | >= 3.2 | Astronomical sunrise/sunset for auto-brightness |
| python-dotenv | >= 1.0 | Loading .env configuration |

Optional:

| Package | Version | Purpose |
|---------|---------|---------|
| discord.py | >= 2.0 | Optional Discord message override |

---

## Installation

```bash
git clone https://github.com/jdlarssen/pixoo-dashboard.git
cd pixoo-dashboard
python -m venv .venv
source .venv/bin/activate
pip install .
```

For development (pytest + ruff):

```bash
pip install ".[dev]"
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Required variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DIVOOM_IP` | Pixoo 64 IP address on LAN | `192.168.1.100` |
| `BUS_QUAY_DIR1` | Entur quay ID for direction 1 | `NSR:Quay:XXXXX` |
| `BUS_QUAY_DIR2` | Entur quay ID for direction 2 | `NSR:Quay:XXXXX` |
| `WEATHER_LAT` | Latitude (decimal degrees) | `59.9139` |
| `WEATHER_LON` | Longitude (decimal degrees) | `10.7522` |

Find your quay IDs at [stoppested.entur.org](https://stoppested.entur.org) and coordinates at [latlong.net](https://www.latlong.net).

### Optional variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ET_CLIENT_NAME` | Identifies your app to the Entur API | `pixoo-dashboard` |
| `WEATHER_USER_AGENT` | User-Agent for MET Norway API (required by their terms) | `pixoo-dashboard/1.0` |
| `DISCORD_BOT_TOKEN` | Discord bot token for message override | *(disabled)* |
| `DISCORD_CHANNEL_ID` | Discord channel ID for messages | *(disabled)* |
| `DISCORD_MONITOR_CHANNEL_ID` | Discord channel ID for health monitoring | *(disabled)* |
| `BIRTHDAY_DATES` | Birthday dates for easter egg (MM-DD, comma-separated) | *(none)* |

<details>
<summary>Full .env example</summary>

```bash
# === REQUIRED ===
DIVOOM_IP=192.168.1.100
BUS_QUAY_DIR1=NSR:Quay:XXXXX
BUS_QUAY_DIR2=NSR:Quay:XXXXX
WEATHER_LAT=59.9139
WEATHER_LON=10.7522

# === OPTIONAL ===
# ET_CLIENT_NAME=my-pixoo-dashboard
# WEATHER_USER_AGENT=pixoo-dashboard/1.0 email@example.com
# DISCORD_BOT_TOKEN=your-bot-token-here
# DISCORD_CHANNEL_ID=123456789012345678
# DISCORD_MONITOR_CHANNEL_ID=123456789012345678
# BIRTHDAY_DATES=01-01,06-15
```

</details>

---

## Usage

```bash
# Standard run (requires Pixoo 64 on the network)
python src/main.py

# With custom IP address
python src/main.py --ip 192.168.1.100

# Simulator mode (no hardware -- opens Tkinter window)
python src/main.py --simulated

# Debug mode (saves each frame to debug_frame.png)
python src/main.py --save-frame

# Test weather animation (works well with --simulated)
TEST_WEATHER=rain python src/main.py --simulated
```

Available weather types for `TEST_WEATHER`: `clear`, `rain`, `snow`, `fog`, `cloudy`, `sun`, `thunder`

---

## Running as a Service (macOS launchd)

The project includes a ready-made `com.divoom-hub.dashboard.plist` for automatic startup.

<details>
<summary>Step-by-step setup</summary>

**1. Edit paths in the plist file**

Open `com.divoom-hub.dashboard.plist` and replace `/EDIT/PATH/TO/` with the actual path to the project. Also update the IP address to your Pixoo 64.

**2. Copy to LaunchAgents**

```bash
cp com.divoom-hub.dashboard.plist ~/Library/LaunchAgents/
```

**3. Load the service**

```bash
launchctl load ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist
```

**4. Check status**

```bash
launchctl list | grep divoom
```

**5. Stop the service**

```bash
launchctl unload ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist
```

**6. View logs**

```bash
tail -f /tmp/divoom-hub.log
tail -f /tmp/divoom-hub.err
```

The service starts automatically at login and restarts on crash (but not on clean exit).

</details>

---

## Built with Claude Code

This project was built from scratch with [Claude Code](https://claude.ai/code) -- Anthropic's CLI tool for AI-assisted development. From the first line of Python to the last pixel on the display, Claude has been the development partner.

The entire process followed a structured workflow: requirements definition, architecture planning, phased implementation, testing, and verification -- all driven by conversations with Claude. The project went from idea to finished dashboard in a single day.

It's not an experiment in "let AI write all the code" -- it's a collaborative project where a human defined what to build, made design decisions, and validated results, while Claude handled implementation, debugging, and testing.

---

## Architecture

```
src/
├── main.py                  # Main loop, CLI arguments, orchestration
├── config.py                # All configuration (.env loading, constants)
├── dashboard_state.py       # Dashboard state management and data fetching
├── circuit_breaker.py       # Circuit breaker for API resilience
├── staleness.py             # Data staleness tracking and thresholds
├── watchdog.py              # Hang detection watchdog thread
├── device/
│   ├── pixoo_client.py      # Pixoo 64 communication with rate limiting
│   └── keepalive.py         # Device keep-alive ping and auto-reboot
├── display/
│   ├── fonts.py             # BDF font loading and conversion
│   ├── layout.py            # Zone definitions, colors, pixel coordinates
│   ├── renderer.py          # PIL compositor (state -> 64x64 image)
│   ├── state.py             # DisplayState with dirty flag pattern
│   ├── text_utils.py        # Text sanitization for BDF fonts
│   ├── animation_selector.py # Weather-to-animation selection logic
│   ├── weather_anim.py      # 8 animation types with depth layers
│   └── weather_icons.py     # Pixel art weather icons (10x10 px)
└── providers/
    ├── bus.py               # Entur JourneyPlanner v3 (GraphQL)
    ├── clock.py             # Norwegian time and date formatting
    ├── discord_bot.py       # Discord message override (daemon thread)
    ├── discord_monitor.py   # Health monitoring and status reporting (Discord embeds)
    ├── geocode.py           # Reverse geocoding for Discord status embeds
    ├── sun.py               # Astronomical sunrise/sunset (astral)
    └── weather.py           # MET Norway Locationforecast 2.0
```

### Data Flow

```
main_loop()
  ├── ds.refresh_bus()           → Entur GraphQL API (every 60s)
  ├── ds.refresh_weather()       → MET Norway API (every 600s)
  ├── weather_anim.tick()        → bg/fg RGBA layers (~1 FPS)
  ├── DisplayState.from_now()    → dirty flag check
  ├── render_frame()             → 64x64 PIL image
  ├── client.push_frame()        → Pixoo 64 via HTTP
  │     ├── OK                   → update last_device_success
  │     └── Error                → exponential backoff (3s → 60s)
  └── keep-alive (every 30s)
        ├── client.ping()        → lightweight health check
        └── 5 failures in a row  → client.reboot() + 30s wait
```

**Dirty flag pattern:** `DisplayState` is a dataclass with equality checking. The main loop compares previous and current state -- the image is only re-rendered when something actually changed (new minute, new bus data, new weather).

**Two speeds:** The main loop runs with a 1.0s pause between each iteration. When a weather animation is active, the animation frame updates every iteration (~1 FPS). When the weather is calm, the loop only checks whether state has changed.

---

## APIs

<details>
<summary>Entur JourneyPlanner v3 (bus data)</summary>

**Endpoint:** `https://api.entur.io/journey-planner/v3/graphql`

**Required header:** `ET-Client-Name` -- identifies your app to Entur.

The app sends a GraphQL query fetching `estimatedCalls` for a given quay ID. Each departure provides `expectedDepartureTime` (real-time when available), `aimedDepartureTime`, a `realtime` flag, and destination info.

**Gotchas:**
- Cancelled departures appear in the response -- the app filters them out and requests extra departures to compensate
- Time calculation: `expectedDepartureTime` is ISO 8601 with timezone, converted to countdown minutes via `datetime.fromisoformat()`
- Countdown is clamped to minimum 0 (no negative values)

</details>

<details>
<summary>MET Norway Locationforecast 2.0 (weather data)</summary>

**Endpoint:** `https://api.met.no/weatherapi/locationforecast/2.0/compact`

**Required header:** `User-Agent` -- MET requires identification per their terms of use.

The app uses `If-Modified-Since` caching: the first call downloads the full response, then the `Last-Modified` value is sent back on subsequent requests. MET returns `304 Not Modified` when data hasn't changed, saving bandwidth and respecting the API terms. The cache is stored at module level in Python.

**Response contains:**
- `timeseries` with weather data per time point
- Each time point has `instant` (current), `next_1_hours` and `next_6_hours` forecasts
- `symbol_code` (e.g. `clearsky_day`, `rain_night`) is used for icon and animation selection

**Gotchas:**
- High/low temperature is not a dedicated field -- the app scans all time points for today's date and finds max/min
- `symbol_code` has suffixes (`_day`, `_night`, `_polartwilight`) that must be stripped for icon lookup
- The API updates approximately every 10 minutes

</details>

---

## Discord Message Override

An optional Discord bot lets you push short messages to the display. The bot runs in a background thread (daemon) and is fully independent of the main loop.

**Setup:**
1. Create a Discord bot at [discord.com/developers](https://discord.com/developers/applications)
2. Enable "Message Content Intent"
3. Invite the bot to a server and channel
4. Add `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` to `.env`

**Usage:**
- Send a message in the channel -- it appears in the weather zone on the display
- Send `clear`, `cls`, or `reset` to remove the message
- The bot reacts with a checkmark to confirm receipt

The message appears in the lower part of the weather zone (below temperature and high/low). When a message is active, the precipitation indicator is hidden to make room.

If `DISCORD_BOT_TOKEN` or `DISCORD_CHANNEL_ID` is not set, the bot simply doesn't start -- no error message, no impact on the dashboard.

---

## Weather Animations

The weather zone (24 pixels tall) has animated overlays that bring the display to life. The system uses a 3D depth effect with two layers:

- **Background layer** (behind text): distant, dimmer particles
- **Foreground layer** (in front of text): close, brighter particles

Each frame is rendered by placing the background layer under the text and the foreground layer over it -- creating an illusion of depth on a flat 64x64 screen.

<details>
<summary>Animation types</summary>

| Type | Description |
|------|-------------|
| **Rain** | Blue drops in two depths -- distant drops are dimmer and shorter, near drops are brighter with 3px streaks |
| **Snow** | Crystals in + shape (near, bright) and single pixels (distant, dim) drifting slowly |
| **Sun** | Corner-anchored sun body with golden rays fanning downward |
| **Clouds** | Grey-white cloud ellipses drifting slowly through the zone |
| **Thunder** | Rain + lightning every ~4 seconds with a 3-frame cycle (flash, afterglow, fade) |
| **Fog** | Cloud blobs drifting through the right side of the zone |
| **Clear night** | Twinkling stars with a 4-state cycle (dark, brighten, peak, dim) |
| **Composite** | Multiple animations layered together (e.g. heavy rain + fog overlay) |

**Weather-to-animation mapping:** Partly cloudy uses sun (day) or clear night (night). Sleet uses rain.

</details>

### Layered Animations and Wind Effect

The animation system supports composite effects when weather conditions warrant it:

- **Intensity scaling:** Snow and rain animations adjust particle count based on precipitation amount (light < 1mm, moderate 1--3mm, heavy > 3mm, extreme > 5mm)
- **Wind effect:** When it's windy, horizontal drift is added to particles based on actual wind direction and speed from the MET API
- **Combo rules:** Heavy rain (> 3mm) automatically adds fog on top. Thunder and rain with strong wind (> 5 m/s) get wind drift. Snow with wind > 3 m/s drifts sideways.

Animations run at ~1 FPS (1.0s between frames). Alpha values are tuned for LED hardware visibility (65--180 range).

---

## Norwegian Characters and Fonts

The display uses BDF bitmap fonts in three sizes:

| Font | Size | Used for |
|------|------|----------|
| 4x6 | 4x6 px | High/low temperature, precipitation, messages |
| 5x8 | 5x8 px | Clock, date, bus countdowns |
| 7x13 | 7x13 px | Available, not in use |

Fonts are loaded from the `assets/fonts/` directory. BDF files are automatically converted to PIL format (`.pil` + `.pbm`) on first run -- these generated files are in `.gitignore`.

Norwegian special characters (ae, oe, aa) are included in the BDF fonts and used in day names: **lordag** and **sondag** contain oe. The clock provider (`clock.py`) uses its own Norwegian lookup tables for day and month names instead of the system locale -- this avoids dependency on installed language support.

---

## Error Handling

The dashboard is designed to run 24/7 unattended. Multiple layers of error handling keep it stable:

**Staleness tracking (stale data):**

| Data source | Stale (aging) | Too old (not displayed) |
|-------------|---------------|-------------------------|
| Bus | > 3 min | > 10 min |
| Weather | > 30 min | > 1 hour |

- When data is *stale* but usable: displayed with an orange dot in the upper right corner of the zone
- When data is *too old*: replaced with `--` placeholders
- On API error: the last successful data is kept and continues to be displayed

**Device connection:**
- The `pixoo` library's `refresh_connection_automatically` prevents the connection from locking up after ~300 push operations
- Rate limiting: minimum 1.0 second between frames (prevents dropped frames from timing jitter)
- Brightness capped at 90% (`MAX_BRIGHTNESS`) -- full brightness can crash the device
- Network errors (timeout, connection loss) are caught and logged -- the dashboard keeps running and retries on the next iteration

**Resilience (keep-alive and recovery):**
- **Keep-alive ping:** Every 30 seconds the client sends a lightweight ping to the device to prevent WiFi power-saving mode from disconnecting
- **Exponential backoff:** On communication errors, a wait period starts at 3 seconds and doubles for each subsequent failure (3s -> 6s -> 12s -> 24s -> ...) up to a max of 60 seconds. Resets to 3s on the first successful communication
- **Auto-reboot:** After 5 consecutive device failures, a `Device/SysReboot` command is sent. The system then waits 30 seconds for the device to reconnect before resuming normal operation
- All three mechanisms work together: ping detects problems early, backoff prevents overwhelming a struggling device, and reboot is the last resort when nothing else works

**Auto-brightness (astronomical):**
- Uses the `astral` library to calculate actual sunrise, sunset, and civil twilight based on latitude/longitude
- Day (after morning twilight): 90% brightness
- Night (after evening twilight): 20% -- readable without lighting up the room
- Follows the seasons automatically: in December it dims as early as 3--4 PM, in June it stays bright until 10--11 PM

---

## Birthday Surprise

Configure birthday dates in `.env` with `BIRTHDAY_DATES` (comma-separated MM-DD format):

```bash
BIRTHDAY_DATES=01-01,06-15
```

On these dates the display gets a festive touch:
- Clock text turns **golden**
- Date text turns **pink**
- A small **5x5-pixel crown** appears in the upper right corner
- **Sparkle pixels** in the clock/date zone (deterministic positions -- no flickering between frames)

---

## License

MIT License -- see [LICENSE](LICENSE) for details.
