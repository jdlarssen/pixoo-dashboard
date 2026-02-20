# Architecture Research

**Domain:** Embedded LED pixel display dashboard (Divoom Pixoo 64)
**Researched:** 2026-02-20
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ EnTur API    │  │ Yr/MET API   │  │ System Clock │              │
│  │ (GraphQL)    │  │ (REST/JSON)  │  │ (local)      │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                      │
├─────────┴─────────────────┴──────────────────┴──────────────────────┤
│                       DATA COLLECTORS                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Bus Fetcher  │  │ Weather      │  │ Time         │              │
│  │ (60s cycle)  │  │ Fetcher      │  │ Provider     │              │
│  │              │  │ (10-15min)   │  │ (continuous) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                      │
├─────────┴─────────────────┴──────────────────┴──────────────────────┤
│                        DATA STORE (in-memory)                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  DisplayState: { bus, weather, time, message_override }  │       │
│  └──────────────────────────┬───────────────────────────────┘       │
│                             │                                       │
├─────────────────────────────┴───────────────────────────────────────┤
│                        RENDER ENGINE                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Layout       │  │ PIL/Pillow   │  │ Pixel Font   │              │
│  │ Manager      │  │ Canvas       │  │ Renderer     │              │
│  │ (zones)      │  │ (64x64 RGB)  │  │              │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                      │
├─────────┴─────────────────┴──────────────────┴──────────────────────┤
│                        DISPLAY DRIVER                               │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Pixoo HTTP Client (Draw/SendHttpGif → device LAN IP)   │       │
│  │  Rate-limited: max 1 push/second                        │       │
│  └──────────────────────────┬───────────────────────────────┘       │
│                             │                                       │
├─────────────────────────────┴───────────────────────────────────────┤
│                        HARDWARE                                     │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Divoom Pixoo 64 (64x64 RGB LED, Wi-Fi, HTTP on :80)   │       │
│  └──────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘

Side channel (interrupt):
  ┌──────────────┐
  │ Message API  │──→ DisplayState.message_override ──→ Render Engine
  │ (HTTP/CLI)   │
  └──────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Bus Fetcher | Queries EnTur GraphQL for next departures from Ladeveien quays | `aiohttp` POST to `api.entur.io/journey-planner/v3/graphql`, 60s interval |
| Weather Fetcher | Queries Yr/MET locationforecast/2.0 for Trondheim weather | `aiohttp` GET to `api.met.no`, 10-15min interval, respects `Expires` header |
| Time Provider | Supplies current time/date in Norwegian locale | Python `datetime` with `locale` or manual Norwegian day/month names |
| Data Store | Holds current display state, notifies renderer on change | Simple dataclass or dict, no persistence needed |
| Layout Manager | Defines pixel zones for each info block on the 64x64 canvas | Static zone definitions (x, y, width, height per section) |
| PIL Canvas | Composites text, icons, and shapes into a 64x64 RGB image | `PIL.Image.new("RGB", (64, 64))` + `PIL.ImageDraw` |
| Pixel Font Renderer | Draws text in tiny pixel fonts readable at low resolution | Custom bitmap font or PICO-8 font from pixoo library |
| Pixoo HTTP Client | Sends rendered frame to device over LAN | HTTP POST to `http://<device-ip>/post` with `Draw/SendHttpGif` payload |
| Message API | Accepts custom messages that temporarily override the display | Simple HTTP endpoint or CLI command writing to data store |

## Recommended Project Structure

```
divoom-hub/
├── src/
│   ├── main.py              # Entry point, scheduler setup, main loop
│   ├── config.py            # Device IP, API keys, stop IDs, intervals
│   ├── collectors/          # Data source fetchers
│   │   ├── __init__.py
│   │   ├── bus.py           # EnTur GraphQL client
│   │   ├── weather.py       # Yr/MET REST client
│   │   └── time_provider.py # Norwegian time/date formatting
│   ├── display/             # Rendering pipeline
│   │   ├── __init__.py
│   │   ├── state.py         # DisplayState dataclass
│   │   ├── layout.py        # Zone definitions for 64x64 canvas
│   │   ├── renderer.py      # PIL compositor (state → 64x64 image)
│   │   ├── fonts.py         # Bitmap font definitions/loader
│   │   └── icons.py         # Weather icon sprites (pre-rendered)
│   ├── device/              # Pixoo communication
│   │   ├── __init__.py
│   │   └── pixoo_client.py  # HTTP driver for Pixoo 64
│   └── messages/            # Custom message injection
│       ├── __init__.py
│       └── handler.py       # Message override logic
├── assets/
│   ├── fonts/               # Pixel font files (if custom)
│   └── icons/               # Weather icon sprites (8x8 or 12x12 pixel art)
├── tests/
│   ├── test_bus.py
│   ├── test_weather.py
│   ├── test_renderer.py
│   └── test_pixoo_client.py
├── pyproject.toml
└── .env                     # Device IP, stop IDs (not committed)
```

### Structure Rationale

- **collectors/:** Each data source is an independent module with its own fetch cycle. Bus and weather have very different refresh rates and error modes. Separation makes testing trivial (mock the HTTP call, verify parsing).
- **display/:** The rendering pipeline is the core complexity. Separating state, layout, fonts, icons, and the compositor allows iterating on the 64x64 layout without touching data fetching or device communication.
- **device/:** Thin wrapper around the Pixoo HTTP API. Could swap to a different display without touching anything else. Also allows a "simulator" mode for development without hardware.
- **messages/:** Isolated so the interrupt/override mechanism does not entangle with the main display loop.

## Architectural Patterns

### Pattern 1: PIL-Based Full-Frame Rendering (Recommended)

**What:** Compose the entire 64x64 display as a PIL Image in Python, then push the complete frame to the Pixoo as a raw image via `Draw/SendHttpGif`. Every pixel is under our control.

**When to use:** Always, for this project. This gives complete control over layout, fonts, and icons on a 64x64 canvas where every pixel matters.

**Trade-offs:**
- PRO: Total control over every pixel, can use any font/icon, consistent rendering
- PRO: Testable without hardware (save PNG, visual diff)
- PRO: No dependency on undocumented native Pixoo font rendering
- CON: Must implement own text rendering (bitmap fonts)
- CON: Slightly more work upfront than native text commands

**Why not native `Draw/SendHttpText`:** The native text command has limited, poorly documented font options (font IDs are not publicly listed, some font/character combos crash the device). On a 64x64 display where every pixel matters, we need pixel-perfect control. Native text also cannot mix text and icons on the same screen in a single composed layout.

**Example:**
```python
from PIL import Image, ImageDraw

def render_frame(state: DisplayState) -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Time zone: top area
    draw_time(draw, state.time, x=0, y=0)

    # Date zone: below time
    draw_date(draw, state.date_str, x=0, y=12)

    # Bus zone: middle
    draw_bus_departures(draw, state.bus_departures, x=0, y=20)

    # Weather zone: bottom
    draw_weather(draw, state.weather, x=0, y=44)

    return img
```

### Pattern 2: Scheduler-Driven Data Collection

**What:** Use `asyncio` with timed tasks (or `APScheduler`) to run each data collector at its own interval. Collectors write to shared state; renderer reads from shared state.

**When to use:** When data sources have different refresh cadences (bus=60s, weather=600s, time=every frame).

**Trade-offs:**
- PRO: Each source refreshes independently, failure in one does not block others
- PRO: Minimizes API calls (weather does not re-fetch every 60s)
- CON: Shared state needs thread/async safety (trivial with asyncio)

**Example:**
```python
import asyncio

async def bus_collector(state: DisplayState):
    while True:
        try:
            state.bus_departures = await fetch_bus_departures()
        except Exception as e:
            log.warning(f"Bus fetch failed: {e}")
            # Keep stale data, mark as stale
        await asyncio.sleep(60)

async def weather_collector(state: DisplayState):
    while True:
        try:
            state.weather = await fetch_weather()
        except Exception as e:
            log.warning(f"Weather fetch failed: {e}")
        await asyncio.sleep(600)

async def render_loop(state: DisplayState, pixoo_client):
    while True:
        frame = render_frame(state)
        await pixoo_client.push_image(frame)
        await asyncio.sleep(1)  # Max 1 push/second
```

### Pattern 3: Message Override with Timeout

**What:** Custom messages temporarily replace the normal display, then automatically revert after a timeout.

**When to use:** For the "push a message to the display" requirement.

**Trade-offs:**
- PRO: Simple state flag, no complex routing
- CON: Only one message at a time (fine for this use case)

**Example:**
```python
@dataclass
class DisplayState:
    bus_departures: list = field(default_factory=list)
    weather: WeatherData | None = None
    time: datetime | None = None
    message_override: str | None = None
    message_expires: datetime | None = None

def render_frame(state: DisplayState) -> Image.Image:
    if state.message_override and datetime.now() < state.message_expires:
        return render_message(state.message_override)
    if state.message_override:
        state.message_override = None  # Expired, clear it
    return render_dashboard(state)
```

## Data Flow

### Main Data Flow

```
[EnTur API]                    [Yr/MET API]            [System Clock]
     │                              │                        │
     │ GraphQL POST (60s)           │ GET (10-15min)         │ (continuous)
     │                              │                        │
     v                              v                        v
[Bus Collector]             [Weather Collector]       [Time Provider]
     │                              │                        │
     │ parse departures             │ parse forecast          │ format NO
     │                              │                        │
     v                              v                        v
┌────────────────────────────────────────────────────────────────┐
│                    DisplayState (in-memory)                     │
│  .bus_departures = [{line, dest, minutes_until}, ...]          │
│  .weather = {temp, symbol_code, high, low, rain_expected}      │
│  .time = "14:32"                                               │
│  .date_str = "tor 20. feb"                                     │
│  .message_override = None | "Custom text"                      │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             v
                    [Render Engine]
                    PIL Image.new("RGB", (64,64))
                             │
                    compose zones:
                    ├── time text (top)
                    ├── date text
                    ├── bus lines + minutes
                    ├── weather icon + temp
                    └── rain indicator
                             │
                             v
                    [64x64 RGB Image]
                             │
                    convert to base64 RGB pixel array
                             │
                             v
                    [Pixoo HTTP Client]
                    POST http://<ip>/post
                    {"Command": "Draw/SendHttpGif",
                     "PicNum": 1, "PicOffset": 0,
                     "PicWidth": 64, "PicSpeed": 1000,
                     "PicData": "<base64>"}
                             │
                             v
                    [Pixoo 64 Display]
```

### Pixoo Wire Protocol Detail

The Pixoo 64 accepts HTTP POST requests to `http://<device-ip>/post` (port 80). The payload for pushing a full frame:

```json
{
    "Command": "Draw/SendHttpGif",
    "PicNum": 1,
    "PicOffset": 0,
    "PicWidth": 64,
    "PicSpeed": 1000,
    "PicData": "<base64-encoded RGB pixel data>"
}
```

**Image encoding process:**
1. Create 64x64 RGB PIL Image
2. Get raw pixel data: `list(img.getdata())` produces 4096 `(R, G, B)` tuples
3. Flatten to byte array: `[R, G, B, R, G, B, ...]` (64 * 64 * 3 = 12,288 bytes)
4. Base64 encode the byte array
5. Send as `PicData` string in the JSON payload

**Critical rate limit:** Do not push more than 1 frame per second. The device becomes unresponsive after rapid pushes. After approximately 300 pushes, the device may stop responding entirely (firmware bug); use `refresh_connection_automatically=True` in the pixoo library or periodically reset the internal counter.

### EnTur Departure Query

```graphql
{
  quay(id: "NSR:Quay:<QUAY_ID>") {
    name
    estimatedCalls(numberOfDepartures: 4) {
      expectedDepartureTime
      destinationDisplay {
        frontText
      }
      serviceJourney {
        line {
          publicCode
        }
      }
    }
  }
}
```

**Endpoint:** `POST https://api.entur.io/journey-planner/v3/graphql`
**Required header:** `ET-Client-Name: <company>-<application>` (e.g., `jdl-divoomhub`)
**Stop IDs:** Use `stoppested.entur.org` to find NSR:Quay IDs for Ladeveien (two quays, one per direction). Query each quay separately to get direction-specific departures.

### Yr/MET Weather Query

```
GET https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=63.43&lon=10.40
```

**Required header:** `User-Agent: divoom-hub/1.0 github.com/<user>/divoom-hub`
**Caching:** Store `Expires` and `Last-Modified` headers. Use `If-Modified-Since` on subsequent requests. Respect 304 Not Modified responses. Do not request more often than the `Expires` header indicates.
**Response fields used:**
- `timeseries[0].data.instant.details.air_temperature` (current temp)
- `timeseries[0].data.next_1_hours.summary.symbol_code` (weather icon)
- Extract today's high/low from timeseries entries
- `precipitation_amount` in `next_1_hours` or `next_6_hours` for rain indicator

**Weather icons:** The `symbol_code` (e.g., `clearsky_day`, `rain`, `partlycloudy_night`) maps directly to filenames in the `metno/weathericons` GitHub repo (MIT licensed, available as PNG/SVG). These must be converted to tiny pixel art sprites (8x8 or 12x12) for the 64x64 display.

## Rendering Pipeline Detail

### Canvas Zones (Preliminary Layout)

```
┌────────────────────────────────────────────────────────────────┐
│  64 pixels wide                                                │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ TIME (large)                              00:00          │  │ y=0..11
│  │ 14:32                                                    │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ DATE                                   tor 20. feb      │  │ y=12..19
│  ├──────────────────────────────────────────────────────────┤  │
│  │ BUS DIR 1                                                │  │ y=20..31
│  │ 3 Sentrum     4m                                         │  │
│  │ 3 Sentrum    19m                                         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ BUS DIR 2                                                │  │ y=32..43
│  │ 3 Lade        2m                                         │  │
│  │ 3 Lade       17m                                         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ WEATHER       [icon] 4°C  H:7° L:1°  [rain]            │  │ y=44..63
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

**Font requirements:** At 64x64, a readable character is roughly 3x5 or 4x6 pixels. The PICO-8 font built into the `pixoo` library renders at approximately 4 pixels wide per character. With a 64-pixel width, that allows roughly 16 characters per line (with minimal spacing). This is tight but workable for bus departure info.

### Bitmap Font Strategy

Use the PICO-8 pixel font from the `pixoo` library for consistency, or define a custom bitmap font. The `pixoo` library supports characters: `0-9 a-z A-Z !'()+,-<=>?[]^_:;./{|}~$@%` which covers Norwegian time/date needs, but Norwegian characters (e, o with diacritics) may need custom glyph additions.

**Important:** Norwegian characters like a-ring, o-slash, ae are not in the PICO-8 character set. Options:
1. Use ASCII approximations in date strings (e.g., "feb" not "feb" is fine, but day names like "onsdag" are fine, "lordag" instead of "lordag" may work)
2. Add custom bitmap glyphs for the 3-4 Norwegian special characters needed
3. Use PIL's built-in bitmap font rendering with a pixel-appropriate .pil/.pbm font

### Weather Icon Pipeline

1. Start from `metno/weathericons` SVG files (MIT licensed)
2. Pre-render to tiny pixel art sprites (8x8, 10x10, or 12x12 pixels)
3. Store as PNG files in `assets/icons/`
4. Map `symbol_code` from Yr API to icon filename
5. Paste icon onto canvas at weather zone position using `img.paste()`

This is a manual pixel art step -- the SVG icons must be hand-adapted to look good at 8-12 pixels. Automated downscaling of SVGs will produce unreadable blobs. Budget time for this.

## Anti-Patterns

### Anti-Pattern 1: Using Native Pixoo Text Commands for Dashboard

**What people do:** Use `Draw/SendHttpText` for text areas and try to compose a dashboard from multiple native text overlays.
**Why it's wrong:** Native text commands operate independently -- you cannot precisely control pixel-level layout when mixing text zones. Font options are limited and poorly documented. Some font/character combos crash the device. You lose the ability to render icons and text in a unified composition.
**Do this instead:** Render the entire 64x64 frame as a PIL Image and push as a single frame via `Draw/SendHttpGif`. Full control, no surprises.

### Anti-Pattern 2: Pushing Frames Too Fast

**What people do:** Push a new frame every time any data changes, or run the render loop faster than 1 Hz.
**Why it's wrong:** The Pixoo 64 becomes unresponsive when pushed faster than ~1 frame/second. After ~300 rapid pushes, it stops responding entirely until connection reset.
**Do this instead:** Render loop at 1-second intervals maximum. If nothing changed, skip the push. Use a "dirty" flag on the display state.

### Anti-Pattern 3: Coupling Data Fetching to Rendering

**What people do:** Fetch bus data inside the render function, blocking the display update while waiting for network.
**Why it's wrong:** Network failures or slow responses freeze the display. Bus API timeout should not prevent time from updating.
**Do this instead:** Async collectors write to shared state. Renderer reads state independently. If a collector fails, stale data is still displayed (better than a frozen display).

### Anti-Pattern 4: Not Handling Yr Caching Headers

**What people do:** Poll `api.met.no` every few minutes regardless of cache headers.
**Why it's wrong:** MET.no will throttle or block your client. The API returns `Expires` headers for a reason -- compact forecasts update roughly every hour for the near-term.
**Do this instead:** Store the `Expires` and `Last-Modified` headers. Only re-request after expiry, using `If-Modified-Since`. Handle 304 gracefully.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| EnTur Journey Planner v3 | GraphQL POST, 60s polling | Header: `ET-Client-Name`. Stop IDs from `stoppested.entur.org`. Returns real-time estimated departures. |
| Yr/MET Locationforecast 2.0 | REST GET, cache-driven polling | Header: `User-Agent` (mandatory, 403 without). Respect `Expires`, use `If-Modified-Since`. Compact format sufficient. |
| Pixoo 64 Device | HTTP POST to `<ip>/post`, max 1/s | LAN-only. `Draw/SendHttpGif` for full-frame push. `Draw/SendHttpText` available but not recommended for dashboard. |
| Weather Icons (metno/weathericons) | Static asset, build-time | Download SVGs, hand-convert to pixel art sprites, bundle in `assets/`. MIT licensed. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Collectors -> State | Direct write (async-safe) | Each collector owns its slice of state. No cross-collector dependencies. |
| State -> Renderer | Read-only access | Renderer never mutates state. Reads current snapshot to compose frame. |
| Renderer -> Pixoo Client | PIL Image hand-off | Renderer produces `Image`, client converts to wire format and POSTs. |
| Message Handler -> State | Write `message_override` | Sets override text + expiry timestamp. Renderer checks before normal render. |

## Build Order (Dependencies)

The architecture has clear dependency layers. Build bottom-up:

```
Phase 1: Device Communication
  └── Pixoo HTTP client (can push a solid-color test frame)
  └── Simulator mode (save PNG locally for testing without device)

Phase 2: Render Engine
  └── PIL canvas creation, bitmap font rendering
  └── Static test: render a hardcoded time/bus/weather layout to PNG
  └── Depends on: Phase 1 (to see results on device)

Phase 3: Data Collectors (can be parallelized)
  ├── Bus collector (EnTur GraphQL)
  ├── Weather collector (Yr/MET)
  └── Time provider (trivial)
  └── Depends on: nothing (can test with mock data)

Phase 4: Integration
  └── Scheduler wiring (asyncio tasks)
  └── State management, dirty-flag optimization
  └── Depends on: Phases 1, 2, 3

Phase 5: Custom Messages
  └── Message injection API
  └── Override/timeout logic
  └── Depends on: Phase 4

Phase 6: Polish
  └── Weather icon pixel art
  └── Norwegian locale refinement
  └── Error recovery, logging, systemd service
  └── Depends on: Phase 4
```

**Key insight:** The render engine and data collectors can be developed in parallel. The render engine can be tested with hardcoded data and PNG output. The collectors can be tested with print statements. They meet at the integration phase.

## Library Decision: pixoo Library vs Raw HTTP

**Recommendation: Use the `pixoo` Python library initially, with the option to drop to raw HTTP if needed.**

The `pixoo` library (v0.9.2, Python 3.10+, PyPI) provides:
- `draw_pixel()`, `draw_text()`, `draw_image()`, `push()` primitives
- Built-in PICO-8 pixel font
- Simulator mode (tkinter GUI) for development without hardware
- Automatic connection refresh to work around the ~300-push firmware bug
- `send_image(PIL.Image)` for pushing complete PIL Image frames

However, the library's built-in drawing primitives are limited for a complex dashboard. The recommended approach is:
1. Use `pixoo` library for **device communication** (`push()`, connection management, simulator)
2. Use **PIL/Pillow directly** for compositing the 64x64 frame (more flexible than pixoo's draw methods)
3. Hand the composed PIL Image to `pixoo.send_image()` for transmission

This gives us the best of both worlds: pixoo handles the finicky device protocol, PIL handles the rendering.

**Fallback:** If the `pixoo` library causes issues (it is a community project, NC-SA licensed), the raw HTTP protocol is simple enough to implement directly: one HTTP POST with a JSON payload containing base64-encoded pixel data.

## Sources

- [SomethingWithComputers/pixoo](https://github.com/SomethingWithComputers/pixoo) - Primary Python library for Pixoo 64 (MEDIUM-HIGH confidence, verified via PyPI + GitHub README)
- [Grayda/pixoo_api NOTES.md](https://github.com/Grayda/pixoo_api/blob/main/NOTES.md) - Reverse-engineered API documentation (MEDIUM confidence, community-sourced)
- [itsmikethetech/Pixoo-64-Tools](https://github.com/itsmikethetech/Pixoo-64-Tools) - Reference architecture for Pixoo 64 projects (MEDIUM confidence)
- [EnTur Journey Planner v3](https://developer.entur.org/pages-journeyplanner-journeyplanner/) - Official departure board API (HIGH confidence, official docs)
- [EnTur GraphQL query example](https://www.bitbrb.com/electronics/graphql-querying-a-bus) - Practical GraphQL query for bus departures (MEDIUM confidence, verified against official API structure)
- [hfurubotten/enturclient](https://github.com/hfurubotten/enturclient) - Python client for EnTur departures (MEDIUM confidence)
- [Yr Locationforecast HowTO](https://developer.yr.no/doc/locationforecast/HowTO/) - Official Yr API usage guide (HIGH confidence, official docs)
- [MET Locationforecast data model](https://docs.api.met.no/doc/locationforecast/datamodel.html) - Official data model docs (HIGH confidence)
- [metno/weathericons](https://github.com/metno/weathericons) - Official weather icon set (HIGH confidence, MIT licensed)
- [Home Assistant Pixoo64 text blueprint](https://community.home-assistant.io/t/divoom-pixoo64-send-text-4-lines/554428) - `Draw/SendHttpText` payload format (MEDIUM confidence, community-verified)
- [Divoom official API docs](http://doc.divoom-gz.com/web/#/12) - Official but poorly maintained API reference (LOW-MEDIUM confidence)

---
*Architecture research for: Divoom Pixoo 64 Entryway Dashboard*
*Researched: 2026-02-20*
