# Technology Stack

**Project:** Divoom Hub -- Pixoo 64 Entryway Dashboard
**Researched:** 2026-02-20

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.13.x | Application runtime | The Pixoo ecosystem is overwhelmingly Python. The best library (`pixoo` by SomethingWithComputers) requires Python >=3.10. Python's Pillow library is the natural choice for 64x64 image rendering. Node.js Pixoo libraries exist but are fewer, less maintained, and less documented. Go with the ecosystem. | HIGH |

### Device Communication

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pixoo (SomethingWithComputers) | 0.9.2 | Pixoo 64 LAN communication | The most mature and well-documented Python library for the Pixoo 64. Provides `draw_image()`, `draw_text_at_location_rgb()`, `push()`, `set_brightness()`, `set_channel()`, `set_clock()`, and simulator support. Used by pixoo-rest and the Home Assistant integration. The alternative libraries (APIxoo, pixoo1664, Pixoo64-Advanced-Tools) are either server-focused, BLE-based, or GUI tools -- not suitable for a headless dashboard service. | HIGH |

**Critical note on `pixoo` library:** The device HTTP API endpoint is `http://{device-ip}/post` with JSON payloads. The `pixoo` library wraps this. Key constraint: do not call `push()` more than once per second or the device stops responding. Known firmware bug: buffer artifacts after ~300 screen updates (previous image remnants). Mitigation: send full-frame images rather than incremental draws.

**Recommended approach:** Render complete 64x64 frames using Pillow, then use `pixoo.draw_image(pil_image)` followed by `pixoo.push()`. This is more reliable than using the library's individual draw primitives because you control the entire frame buffer. The pixoo-rest project and Home Assistant integration both use this PIL-based approach.

### Image Rendering

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pillow (PIL Fork) | 12.1.1 | 64x64 frame rendering | The standard Python imaging library. Provides `Image.new("RGB", (64, 64))`, `ImageDraw` for shapes/text/lines, and `ImageFont` for bitmap font rendering. Perfect for compositing a dashboard layout onto a tiny canvas. The `pixoo` library accepts PIL Image objects directly via `draw_image()`. | HIGH |

### Weather API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| metno-locationforecast | 2.1.0 | MET Norway / Yr weather data | Production-stable Python wrapper for MET's Locationforecast 2.0 API. Handles automatic caching (respects Expires headers), provides structured access to temperature, precipitation, wind, cloud cover, humidity, and symbol codes. Released Dec 2024, supports Python 3.9-3.13. The alternative `yr-weather` (v0.4.0, Oct 2023) is less actively maintained and has fewer features. | HIGH |

**MET API details (Locationforecast 2.0):**
- Endpoint: `https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}`
- Format: GeoJSON with forecast data
- Compact response includes: `air_temperature`, `precipitation_amount`, `wind_speed`, `wind_from_direction`, `cloud_area_fraction`, `relative_humidity`, `symbol_code` (weather icon identifier)
- **Required:** Custom User-Agent header (e.g., `divoom-hub/1.0 github.com/user/repo`). Missing/generic = 403 Forbidden. Fake = permanent blacklist.
- **Required:** Cache responses using `Expires` and `Last-Modified` headers. Use `If-Modified-Since` for conditional requests.
- **Rate limit:** No fixed limit published, but aggressive polling will get you throttled (429) or blocked. Weather data refreshes every ~1 hour; polling every 10-15 minutes is sensible.
- Coordinates for Trondheim: lat=63.4305, lon=10.3951 (4 decimal max or you get blocked)
- `symbol_code` values map to weather icons (e.g., `clearsky_day`, `cloudy`, `rain`, `heavyrain`, `snow`). Official icon set available at https://github.com/nrkno/yr-weather-symbols

### Transit API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| requests | 2.32.x | HTTP client for Entur GraphQL API | Direct GraphQL queries via `requests.post()` are simpler than using the deprecated Entur SDK or the async `enturclient` (last updated 2022). The Entur API is a standard GraphQL endpoint -- no SDK needed. `requests` is battle-tested and has zero learning curve. | HIGH |

**Entur API details (Journey Planner v3):**
- Endpoint: `https://api.entur.io/journey-planner/v3/graphql`
- Method: POST with JSON body `{"query": "...", "variables": {...}}`
- **Required header:** `ET-Client-Name: yourusername-divoomhub` (format: `<company>-<application>`). Unidentified consumers get strict rate limiting or blocking.
- **No authentication required** for public data (Journey Planner is open under NLOD license)
- Stop IDs: Use https://stoppested.entur.org/ to find `NSR:StopPlace:XXXXX` and `NSR:Quay:XXXXX` IDs for Ladeveien (both directions = two different quay IDs)
- GraphQL IDE for testing: https://api.entur.io/graphql-explorer/journey-planner-v3

**Example GraphQL query for departures:**
```graphql
{
  quay(id: "NSR:Quay:XXXXX") {
    name
    estimatedCalls(numberOfDepartures: 3) {
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

**Why NOT use `enturclient`:** Last release was v0.2.4 (July 2022). The Entur SDK (@entur/sdk for Node.js) is officially deprecated. The GraphQL API is stable and simple enough to query directly with `requests`. Fewer dependencies = fewer breakage points.

### Pixel Fonts

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Custom BDF/PCF bitmap fonts via Pillow | N/A | Tiny readable text on 64x64 | Pillow's `ImageFont.load()` supports bitmap fonts in PIL format (converted from BDF/PCF via `pilfont`). For a 64x64 display, you need 4x6, 5x7, or 5x8 pixel fonts. TrueType fonts at small sizes produce anti-aliasing artifacts that look terrible on LED pixels. BDF bitmap fonts render pixel-perfect. | MEDIUM |

**Font sources with Norwegian character support (ae, oe, aa):**
- `font8x8` (github.com/dhepper/font8x8) -- 8x8 monochrome, includes Latin Extended (U+0000-U+00FF covering ae/oe/aa). Available as C headers, needs conversion.
- `Matrix-Fonts` (github.com/trip5/Matrix-Fonts) -- BDF format, designed for LED matrix displays, multiple sizes
- `Tomorrow Night` pixel font (v3x3d.itch.io) -- Explicit Norwegian support, 8x10 TTF
- Pillow's built-in PICO-8 font via the `pixoo` library -- but limited character set, may lack ae/oe/aa

**Recommended approach:** Source a BDF font at 5x7 or 5x8 pixels that includes Latin Extended characters (U+00E6 ae, U+00F8 oe, U+00E5 aa). Convert to PIL format with `pilfont`. Test on simulator before device. If no suitable BDF font has Norwegian support, use a small TrueType pixel font (like Cozette, Tamzen, or Terminus) loaded via `ImageFont.truetype()` at the exact design size with `fontmode='1'` to disable anti-aliasing.

**Confidence note:** Finding a pre-made BDF font that is both tiny enough (5x7) AND has Norwegian characters may require testing multiple options. This is a known pain point that needs hands-on experimentation during implementation. Flag for phase-specific research.

### Scheduling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| asyncio (stdlib) | N/A (Python stdlib) | Periodic task scheduling | Built into Python, zero dependencies. A simple `while True: await asyncio.sleep(60)` loop is sufficient for "refresh bus data every minute, weather every 10 minutes." No need for `schedule`, `APScheduler`, or cron. The app is a single long-running process with two periodic tasks at different intervals. asyncio handles this natively. | HIGH |

**Why NOT `schedule` library:** It requires a polling loop (`schedule.run_pending()` + `time.sleep(1)`) which is wasteful. asyncio's event loop is cleaner for a daemon process. Also, `schedule` doesn't support async functions natively, and the Entur API calls benefit from async HTTP (though sync `requests` is fine for the low request volume here).

**Alternative consideration:** If you want the simplest possible approach (no async), a plain `time.sleep()` loop with `requests` (synchronous) works fine for this use case. Two API calls per minute is trivially low. The decision between sync and async is a taste preference, not a technical requirement.

**Recommended:** Start synchronous (simpler to debug). Only move to async if you need concurrent API calls or the refresh loop timing becomes a concern.

### Development & Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pixoo simulator | (bundled) | Test without device | The `pixoo` library includes a Tkinter-based simulator that renders the 64x64 buffer to a GUI window. Supports all `draw_*` methods and `push()`. Essential for layout iteration before the device is on the network. | HIGH |
| pytest | latest | Testing | Standard Python testing. Test data fetching, layout rendering, font handling independently of the device. | HIGH |
| ruff | latest | Linting + formatting | Fast, opinionated Python linter/formatter. Replaces flake8 + black + isort. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Runtime | Python 3.13 | Node.js | Pixoo library ecosystem is Python-dominant. Node options (node-divoom-timebox, pixoo-api) are less maintained and have fewer stars/contributors. Pillow has no Node.js equivalent for pixel-level image composition. |
| Pixoo lib | pixoo (SomethingWithComputers) | APIxoo | APIxoo interacts with Divoom's cloud server, not LAN. We need local/LAN control. |
| Pixoo lib | pixoo (SomethingWithComputers) | Pixoo64-Advanced-Tools | GUI application (customtkinter), not a library. Good for manual use, not for a headless service. |
| Pixoo lib | pixoo (SomethingWithComputers) | Direct HTTP to device | The raw Pixoo API is poorly documented and requires manual base64 encoding of pixel buffers. The library handles this. |
| Weather | metno-locationforecast | yr-weather | yr-weather last updated Oct 2023 (v0.4.0). metno-locationforecast updated Dec 2024 (v2.1.0), supports Python 3.13, production-stable classification. |
| Weather | metno-locationforecast | Direct HTTP to api.met.no | The library handles caching, If-Modified-Since headers, and data parsing. Rolling your own means reimplementing all of that. |
| Transit | Direct GraphQL via requests | enturclient | Last updated July 2022. Async-only (aiohttp). For 2 API calls/minute, a simple `requests.post()` with a GraphQL query string is less code and zero risk of abandoned dependency. |
| Transit | Direct GraphQL via requests | @entur/sdk (Node.js) | Officially deprecated by Entur. |
| Scheduling | asyncio / time.sleep | schedule library | Over-engineered for two periodic tasks. The `schedule` library adds a dependency for something achievable with 3 lines of stdlib code. |
| Scheduling | asyncio / time.sleep | cron | Cron restarts the process each run, losing state. A long-running daemon is simpler for a display that needs continuous updates. |
| Fonts | BDF bitmap via Pillow | TrueType at small sizes | TrueType fonts anti-alias by default, producing blurry text on LED pixels. Bitmap fonts are pixel-perfect. Exception: pixel-designed TTF fonts at exact design size with anti-aliasing disabled. |

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Core dependencies
pip install pixoo                    # Pixoo 64 communication (v0.9.2)
pip install Pillow                   # Image rendering (v12.1.x)
pip install metno-locationforecast   # MET/Yr weather API (v2.1.0)
pip install requests                 # HTTP client for Entur GraphQL (v2.32.x)

# Dev dependencies
pip install pytest ruff

# Optional: font conversion tool
pip install pillow-scripts           # Provides pilfont for BDF->PIL conversion
```

**requirements.txt:**
```
pixoo>=0.9.2
Pillow>=12.0
metno-locationforecast>=2.1.0
requests>=2.32.0
```

**requirements-dev.txt:**
```
pytest
ruff
```

## Weather Icon Mapping

The `symbol_code` from MET's API (e.g., `clearsky_day`, `rain`, `heavysnow`) needs to be mapped to pixel art icons on the 64x64 display. NRK maintains the official Yr weather symbol set at https://github.com/nrkno/yr-weather-symbols (SVG format). These will need to be redrawn as tiny pixel art sprites (likely 8x8 or 12x12 pixels) for the Pixoo display. This is a manual design task, not a library concern.

## Process Management

For running as a persistent service on macOS or Linux:

| Approach | When | Why |
|----------|------|-----|
| Direct `python main.py` | Development | Simple, interactive |
| launchd plist (macOS) | Production on Mac | Native macOS daemon management, auto-restart on crash |
| systemd unit (Linux) | Production on Linux/Pi | Native Linux daemon management, auto-restart, logging |
| Docker container | If isolation needed | Overkill for a single-purpose dashboard, but clean |

**Recommendation:** Start with direct execution. Add systemd/launchd when the dashboard is stable. Docker is unnecessary unless deploying to a shared machine.

## Sources

### Pixoo 64 / Device Communication
- [pixoo library (SomethingWithComputers)](https://github.com/SomethingWithComputers/pixoo) -- PRIMARY. v0.9.2, Aug 2024. HIGH confidence.
- [pixoo on PyPI](https://pypi.org/project/pixoo/) -- Version/dependency info. HIGH confidence.
- [pixoo-rest wrapper](https://github.com/4ch1m/pixoo-rest) -- Confirms PIL Image workflow. HIGH confidence.
- [Divoom API docs](http://doc.divoom-gz.com/web/#/12?page_id=196) -- Official (sparse) device API reference. MEDIUM confidence (docs are incomplete).
- [Pixoo64-Advanced-Tools](https://github.com/tidyhf/Pixoo64-Advanced-Tools) -- Alternative tool, confirmed as GUI app. HIGH confidence.
- [Home Assistant Pixoo 64 community thread](https://community.home-assistant.io/t/divoom-pixoo-64/420660) -- Real-world usage reports, firmware issues. MEDIUM confidence.

### Weather API (MET Norway / Yr)
- [MET Weather API portal](https://api.met.no/) -- Official API overview. HIGH confidence.
- [Locationforecast HowTo](https://developer.yr.no/doc/locationforecast/HowTO/) -- Official usage guide. HIGH confidence.
- [metno-locationforecast on PyPI](https://pypi.org/project/metno-locationforecast/) -- v2.1.0, Dec 2024. HIGH confidence.
- [metno-locationforecast on GitHub](https://github.com/Rory-Sullivan/metno-locationforecast) -- Usage examples, data fields. HIGH confidence.
- [Yr weather symbols (NRK)](https://github.com/nrkno/yr-weather-symbols) -- Official symbol_code icon set. HIGH confidence.
- [yr-weather (alternative)](https://github.com/ZeroWave022/yr-weather) -- v0.4.0, Oct 2023. Evaluated and rejected. HIGH confidence.

### Transit API (Entur)
- [Entur developer docs](https://developer.entur.org/) -- Official. HIGH confidence.
- [Entur Journey Planner v3](https://developer.entur.org/pages-journeyplanner-journeyplanner/) -- GraphQL API docs. HIGH confidence.
- [Entur authentication/headers](https://developer.entur.org/pages-intro-authentication/) -- ET-Client-Name requirement. HIGH confidence.
- [enturclient Python library](https://github.com/hfurubotten/enturclient) -- v0.2.4, July 2022. Evaluated and rejected (stale). MEDIUM confidence.
- [Entur GraphQL IDE](https://api.entur.io/graphql-explorer/journey-planner-v3) -- Interactive query testing. HIGH confidence.
- [BitBrb GraphQL bus querying tutorial](https://www.bitbrb.com/electronics/graphql-querying-a-bus) -- Real-world query example. MEDIUM confidence.
- [NSR Stop Place Registry](https://stoppested.entur.org/) -- For finding Ladeveien stop/quay IDs. HIGH confidence.

### Pillow / Image Rendering
- [Pillow ImageFont docs](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html) -- Bitmap font support. HIGH confidence.
- [Pillow ImageDraw docs](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) -- Drawing primitives. HIGH confidence.
- [Pillow releases](https://github.com/python-pillow/Pillow/releases) -- v12.1.1, Feb 2026. HIGH confidence.

### Pixel Fonts
- [font8x8](https://github.com/dhepper/font8x8) -- 8x8 bitmap with Latin Extended. MEDIUM confidence (needs conversion testing).
- [Matrix-Fonts](https://github.com/trip5/Matrix-Fonts) -- BDF fonts for LED matrices. MEDIUM confidence.
- [Tomorrow Night pixel font](https://v3x3d.itch.io/tomorrow-night) -- Norwegian character support confirmed. MEDIUM confidence.

### Python Runtime
- [Python 3.13.12 release](https://www.python.org/downloads/release/python-31312/) -- Feb 2026. HIGH confidence.
- [requests on PyPI](https://pypi.org/project/requests/) -- v2.32.5, Aug 2025. HIGH confidence.
