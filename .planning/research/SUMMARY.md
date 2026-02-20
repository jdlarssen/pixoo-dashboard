# Project Research Summary

**Project:** Divoom Hub — Pixoo 64 Entryway Dashboard
**Domain:** Embedded LED pixel display dashboard with live transit and weather data
**Researched:** 2026-02-20
**Confidence:** HIGH

## Executive Summary

This project is a single-purpose, always-on information dashboard running on a 64x64 LED pixel display (Divoom Pixoo 64). The core problem is constraint: 4,096 pixels must display the current time, today's date in Norwegian, next bus departures from Ladeveien in both directions, current temperature, and a weather icon — simultaneously, at a glance, without rotation. Research conclusively establishes that the correct approach is full-frame pixel rendering: compose the entire 64x64 display as a PIL/Pillow image in Python, then push it to the device via the `Draw/SendHttpGif` HTTP API. Every serious Pixoo 64 dashboard project (pixoo-weather, Home Assistant integration, Node-RED dashboards) converges on this approach. The Pixoo's native text commands cannot coexist with pixel-buffer rendering on the same screen, and the native fonts lack Norwegian character support — making PIL-based custom rendering mandatory, not optional.

The recommended stack is lean and purpose-fit: Python 3.13 with the `pixoo` library (v0.9.2) for device communication, Pillow for image rendering, `metno-locationforecast` for Yr weather data, and direct GraphQL queries via `requests` for Entur transit data. Asyncio is optional — a simple synchronous refresh loop is sufficient for two API calls per minute. The architecture decomposes cleanly into four layers: data collectors (bus + weather + time), shared in-memory state, a render engine (PIL compositor), and a thin device driver. These layers can be developed and tested independently, which is critical for a hardware-dependent project where the display may not always be accessible.

The three risks that matter most are: (1) the Pixoo firmware locks up after ~300 push calls — the connection refresh mechanism must be built in from day one, not added later; (2) the Yr API will ban your IP if you ignore HTTP caching headers — cache-first design is required from the start; (3) fitting all required information into 64x64 pixels at readable font sizes is genuinely hard — layout must be designed with pixel budgets before any code is written. All three risks are preventable if addressed early. None require abandoning the chosen approach.

## Key Findings

### Recommended Stack

The Python ecosystem owns this domain. The `pixoo` library (SomethingWithComputers, v0.9.2) is the uncontested choice for Pixoo 64 communication — it wraps the device's HTTP protocol, provides a Tkinter simulator for development without hardware, handles the ~300-push connection refresh bug, and accepts PIL Image objects directly. Pillow (v12.1.1) handles all image composition. For weather, `metno-locationforecast` (v2.1.0, Dec 2024) is preferred over the older `yr-weather` library and handles caching headers automatically. For transit, direct GraphQL queries via `requests` are better than the stale `enturclient` (last updated July 2022). No SDK, no framework overhead — the scope doesn't warrant it.

The one area of genuine uncertainty is pixel fonts with Norwegian character support. BDF bitmap fonts at 5x7 pixels that also cover Latin Extended (ae, oe, aa) may require testing multiple options before finding one that works. This is flagged as a hands-on experimentation task during Phase 1, not a research problem that can be pre-solved.

**Core technologies:**
- **Python 3.13**: Application runtime — the Pixoo ecosystem is Python-dominant; no comparable Node.js or Go options exist
- **pixoo 0.9.2**: Pixoo 64 LAN communication — most mature library, includes simulator, handles device quirks, accepts PIL Image directly
- **Pillow 12.1.1**: 64x64 frame rendering — accepted by the pixoo library via `draw_image()`; provides full pixel-level control
- **metno-locationforecast 2.1.0**: MET Norway/Yr weather API — handles caching automatically, actively maintained, supports Python 3.13
- **requests 2.32.x**: Entur GraphQL HTTP client — direct GraphQL POST is simpler and safer than any available SDK
- **asyncio (stdlib)**: Periodic task scheduling — zero dependencies, handles multi-interval refresh natively; sync alternative is also viable
- **pytest + ruff**: Testing and linting — standard Python tooling

### Expected Features

The layout constraint (single screen, all data visible simultaneously) is the defining design challenge. Research from existing Pixoo 64 projects shows this is achievable with three vertical zones: time/date at top (~20px), bus departures in the middle (~24px), weather at bottom (~20px). At a readable 5-pixel-wide font with 1-pixel spacing, roughly 10 characters per row and 8 rows are available. Every pixel must be intentional.

**Must have (table stakes):**
- Current time in large pixel font — dominant visual element, readable from 2+ meters
- Today's date in Norwegian ("tor 20. feb") — short day name + day number + short month
- Next 2 bus departures, direction 1 (line number + minutes until departure)
- Next 2 bus departures, direction 2 (line number + minutes until departure)
- Current temperature from Yr
- Weather icon (pixel art sprite, ~12x12 pixels)
- Auto-refresh: bus every 60s, weather every 10-15min (respecting Yr cache headers)
- Single-screen layout — no rotation, no scrolling, all data simultaneously visible

**Should have (differentiators — high value, low effort):**
- Bus departure countdown coloring: green (>10 min), yellow (3-10 min), red (<3 min)
- Auto-brightness: dim at night via `SetBrightness` API on a schedule
- Screen schedule: off at bedtime, on in morning via `set_screen()` API
- Today's high/low temperature ("H:5 L:-2" in small font)
- Rain expected indicator (single icon or color cue near weather zone)
- Graceful error states: staleness indicator when API fails rather than serving stale data silently

**Should have (moderate effort):**
- Custom push message: temporary text overlay with auto-expiry timeout
- Weekend/weekday mode: reclaim bus departure pixels for more weather data on weekends

**Defer (v2+):**
- Animated transitions — device crashes after ~40 frames; adds complexity without value at 64x64
- Multi-page rotation — explicitly against user requirement
- Mobile app or web UI for configuration
- Multi-device support

### Architecture Approach

The architecture is a four-layer pipeline: independent data collectors write to a shared in-memory `DisplayState` dataclass; the render engine reads state and composes a 64x64 PIL Image; the device driver converts the image to base64 RGB and POSTs it to the Pixoo's HTTP endpoint. Layers are decoupled — collectors fail independently (stale data is kept), the renderer never mutates state, and the device driver is swappable with a simulator. This is the architecture used by every mature Pixoo 64 project. Build it bottom-up: device driver first (tested with a solid-color frame), then render engine (tested with hardcoded data and PNG output), then collectors (tested with print statements), then wire them together.

**Major components:**
1. **Data Collectors** (`collectors/`) — Bus fetcher (Entur GraphQL, 60s cycle), weather fetcher (Yr REST, cache-driven), time provider (Norwegian locale formatting)
2. **DisplayState** (`display/state.py`) — In-memory dataclass holding current bus departures, weather, time, and message override; single source of truth for the renderer
3. **Render Engine** (`display/renderer.py`, `layout.py`, `fonts.py`, `icons.py`) — PIL compositor that reads DisplayState and produces a 64x64 RGB Image; testable without hardware
4. **Pixoo Device Driver** (`device/pixoo_client.py`) — Thin wrapper around `pixoo` library; converts PIL Image to wire format, enforces 1-push/second rate limit, manages connection refresh
5. **Message Handler** (`messages/handler.py`) — Optional: writes message override + expiry to DisplayState; renderer checks override before normal render path

### Critical Pitfalls

1. **Pixoo 300-push lockup** — The device firmware locks up completely (requires power cycle) after ~300 `push()` calls. A dashboard pushing every 60 seconds hits this in 5 hours. Prevention: enable `refresh_connection_automatically=True` in the pixoo library from the very first integration. This is non-negotiable in Phase 1.

2. **Yr API IP ban from bad caching** — MET Norway actively bans IPs that ignore `Expires` and `If-Modified-Since` caching headers, with no documented unban timeline. Prevention: use `metno-locationforecast` library (caching built-in) and never roll custom HTTP calls to the MET API endpoint. Also truncate coordinates to 4 decimal places maximum.

3. **Norwegian characters crash native text API** — The Pixoo's `Draw/SendHttpText` does not support ae, oe, aa. Certain font/character combos crash the device. Prevention: this is already addressed by using PIL-based full-frame rendering (the only workable approach anyway). Never use native text commands for this project.

4. **Entur rate limiting via generic or missing client name** — Entur rate-limits by `ET-Client-Name` header. Shared or missing names get heavily throttled. Prevention: include unique `ET-Client-Name: jdl-divoomhub` header from the first request; poll no faster than every 60 seconds; use Quay IDs (not StopPlace IDs) for direction-specific departures.

5. **Cramming too much into 64x64** — At readable font sizes (5x7px minimum), roughly 10 characters per line and 8 lines are available. This is tight. Prevention: design the pixel layout with exact budgets on paper before writing any rendering code. The layout is the hardest design problem in this project.

## Implications for Roadmap

Architecture research defines a clear bottom-up build order based on layer dependencies. FEATURES.md defines MVP scope. PITFALLS.md maps each pitfall to the phase where it must be prevented. The phase structure below integrates all three.

### Phase 1: Foundation — Device Driver + Render Engine + Layout

**Rationale:** Everything else depends on being able to push a pixel-correct frame to the display. The pixel budget must be locked here, before any data integration, to prevent the cramming pitfall from cascading into later phases. Norwegian font support must be validated here since it determines the entire rendering approach.

**Delivers:** A working 64x64 pixel compositor that pushes a hardcoded but correctly laid-out dashboard frame to the Pixoo, demonstrating Norwegian time/date rendering, correct zone proportions, and sustained operation (8+ hours) without device lockup.

**Addresses:**
- Full-frame PIL rendering approach (FEATURES.md: "What MUST Be Custom-Rendered")
- Norwegian character support via bitmap font (FEATURES.md: "Today's date in Norwegian")
- Pixel layout zones locked with exact pixel budgets (FEATURES.md: "Layout Analysis")
- Single-screen all-data-visible constraint validated

**Avoids:**
- Pixoo 300-push lockup (PITFALLS #1) — `refresh_connection_automatically=True` from first integration
- Layout cramming (PITFALLS #5) — pixel budget designed on paper before code is written
- Native text API crashes (PITFALLS #2) — PIL rendering decided here; native text commands never used

**Research flag:** NEEDS PHASE RESEARCH — Norwegian bitmap font with Latin Extended characters at 5x7px needs hands-on testing. Candidate fonts (Matrix-Fonts, font8x8, Cozette, Tamzen) exist but the right choice requires iteration against the simulator. Cannot be resolved without trying them.

---

### Phase 2: Bus Departures

**Rationale:** Bus data is the highest-urgency functional requirement — it is the primary reason this dashboard exists. Building it second (after the rendering pipeline is proven) means real data populates a real layout immediately. The Entur integration is straightforward but requires quay ID lookup before code is written.

**Delivers:** Real-time bus departures from Ladeveien (both directions) displayed in correct layout zones, refreshing every 60 seconds, with graceful fallback when the API fails.

**Uses:** `requests` for GraphQL POST to Entur Journey Planner v3

**Implements:** Bus Fetcher collector, `DisplayState.bus_departures`, bus rendering zone in Render Engine

**Avoids:**
- Entur rate limiting (PITFALLS #4) — unique `ET-Client-Name` header, 60s polling minimum, from first request
- Querying StopPlace instead of Quay — specific NSR:Quay IDs required for direction-specific data (PITFALLS gotcha table)
- Stale data shown as fresh — mark data with timestamp; show staleness indicator on failure

**Research flag:** STANDARD PATTERNS — Entur GraphQL API is well-documented with official IDE for testing. Quay ID discovery via stoppested.entur.org is a mechanical lookup task. No deep research needed, but quay IDs must be found before implementation begins.

---

### Phase 3: Weather Integration

**Rationale:** Weather is the second functional data source. It is simpler than bus data (one API call every ~hour vs every 60s) but has more severe failure modes (IP ban). Building after bus means the caching layer is designed deliberately, not retrofitted under time pressure.

**Delivers:** Current temperature, weather icon (pixel art sprite), high/low temperatures displayed in weather zone, with proper HTTP caching that will not trigger MET Norway rate limits or bans.

**Uses:** `metno-locationforecast 2.1.0` (caching headers handled automatically)

**Implements:** Weather Fetcher collector, `DisplayState.weather`, weather rendering zone, pixel art weather icon sprites in `assets/icons/`

**Avoids:**
- Yr API IP ban (PITFALLS #3) — use `metno-locationforecast` library, not raw HTTP; coordinates to 4 decimals max
- symbol_code day/night confusion (PITFALLS "looks done but isn't") — handle `_day`/`_night`/`_polartwilight` suffixes explicitly
- UTC/local timezone errors — use timezone-aware datetime for Norwegian CET/CEST conversion

**Research flag:** STANDARD PATTERNS — `metno-locationforecast` is well-documented and handles the hard parts. Weather icon pixel art is a manual design task (hand-draw 8-12px sprites from the metno SVG set); budget creative time for it, not research time.

---

### Phase 4: Polish and Differentiators

**Rationale:** Once both data sources are live and the core layout is proven against real-world conditions, add the features that make the dashboard genuinely excellent to use daily. All of these are high-value, low-risk additions that build on the established pipeline.

**Delivers:** Bus countdown coloring, auto-brightness + screen schedule, graceful error state indicators, and optionally a custom push message mechanism.

**Addresses:**
- Bus departure countdown coloring — green/yellow/red based on minutes remaining
- Auto-brightness night dimming via `SetBrightness` API
- Screen schedule on/off via `set_screen()` API
- Graceful error states with staleness indicators
- Custom push message with expiry timeout (optional)

**Avoids:**
- Stale data displayed as fresh without indication (PITFALLS "looks done but isn't") — staleness indicators added here
- WiFi disconnection silently breaking display — reconnection logic verified during extended testing

**Research flag:** STANDARD PATTERNS — `SetBrightness` and `set_screen()` APIs are documented and well-used. Message override is a straightforward state flag with timestamp. No deep research needed.

---

### Phase Ordering Rationale

- **Device driver before everything:** Integrating with the real device must happen early to surface firmware quirks (300-push lockup, buffer artifacts) before they become production surprises that require architectural rework.
- **Layout locked before data:** The pixel budget is the binding constraint. Data integrations must have a stable rendering target. Retrofitting layout after data is wired in requires rewriting the renderer.
- **Bus before weather:** Bus is the primary use case and higher-frequency data. If only one data source works, it should be bus. Weather also has more dangerous failure modes (IP ban) that benefit from being designed deliberately, not rushed.
- **Polish last:** Auto-brightness and screen scheduling are zero-risk additions that require a stable base. Custom push messages require the DisplayState architecture to be settled first.

### Research Flags

**Needs phase research:**
- **Phase 1:** Norwegian bitmap font selection — candidate fonts need real testing in the simulator. Cannot determine the right choice without hands-on testing against the 5x7px target size. Flag for `/gsd:research-phase` during planning.

**Standard patterns (skip research-phase):**
- **Phase 2:** Entur GraphQL — official docs + GraphQL IDE are sufficient; quay ID lookup is a mechanical one-time task
- **Phase 3:** Yr/MET weather — `metno-locationforecast` library handles complexity; pixel art icons are creative work, not research
- **Phase 4:** Polish features — all APIs involved are documented and stable

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core technologies (pixoo, Pillow, metno-locationforecast, requests) all verified via official sources, PyPI, and cross-validated by multiple real-world Pixoo 64 projects. No contested choices. |
| Features | HIGH | Feature requirements are clear from project definition. What is technically feasible at 64x64 pixels is well-established from existing projects. Layout pixel math is verifiable. |
| Architecture | HIGH | PIL-based full-frame rendering is the documented consensus approach across all serious Pixoo 64 dashboard projects. Layer decomposition is standard and well-validated. Wire protocol is reverse-engineered and confirmed by multiple sources. |
| Pitfalls | MEDIUM | Device firmware bugs (300-push lockup, buffer artifacts) are documented by multiple community sources but behavior may vary across firmware versions. Yr caching rules sourced from official docs (HIGH confidence). Entur rate limiting pattern from real HA incident (MEDIUM confidence). |

**Overall confidence: HIGH**

### Gaps to Address

- **Norwegian pixel font:** No pre-vetted font is confirmed to work at 5x7px with full Latin Extended coverage on this specific rendering pipeline. Requires hands-on testing in Phase 1. Fallback: use a small TrueType pixel font (Cozette, Terminus) with `fontmode='1'` to disable anti-aliasing.

- **Ladeveien quay IDs:** Specific NSR:Quay IDs for Ladeveien (both directions) must be looked up via `stoppested.entur.org` before Phase 2 development begins. This is a 5-minute mechanical task, not a research problem, but it blocks Phase 2 implementation.

- **Weather icon pixel art:** The MET Norway weather symbol set (SVG) must be manually redrawn as 8x12 or 12x12 pixel art sprites. Automated SVG downscaling produces unreadable blobs at this resolution. Budget design time in Phase 3.

- **Pixoo firmware version:** The 300-push lockup behavior is documented for firmware versions in use as of 2024-2025. Verify during Phase 1 soak testing (run for 8+ hours continuously). If the device has newer firmware, behavior may differ.

- **`pixoo` library license:** CC-BY-NC-SA 4.0 (non-commercial, share-alike). Fine for a personal project; worth noting if the project ever becomes public or commercial.

## Sources

### Primary (HIGH confidence)
- [SomethingWithComputers/pixoo](https://github.com/SomethingWithComputers/pixoo) — Pixoo 64 Python library, device protocol, simulator, connection refresh behavior
- [MET Weather API / Yr Developer Docs](https://developer.yr.no/doc/locationforecast/HowTO/) — Official Locationforecast 2.0 usage guide, caching requirements, coordinate truncation rules
- [metno-locationforecast on PyPI](https://pypi.org/project/metno-locationforecast/) — v2.1.0, Dec 2024, Python 3.9-3.13 support confirmed
- [Entur Developer Docs](https://developer.entur.org/) — Journey Planner v3 GraphQL API, ET-Client-Name requirement, rate limiting policy
- [Pillow docs](https://pillow.readthedocs.io/en/stable/) — ImageFont, ImageDraw API references
- [metno/weathericons](https://github.com/metno/weathericons) — Official weather icon set, MIT licensed, symbol_code mapping

### Secondary (MEDIUM confidence)
- [Grayda/pixoo_api NOTES.md](https://github.com/Grayda/pixoo_api/blob/main/NOTES.md) — Reverse-engineered API command reference; covers undocumented device behavior including 300-push lockup
- [pixoo-rest](https://github.com/4ch1m/pixoo-rest) — Confirms PIL Image workflow for Pixoo 64 production use
- [pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant) — Reference architecture for PIL-based compositing with multiple element types
- [Entur rate limit HA issue #86547](https://github.com/home-assistant/core/issues/86547) — Real-world rate limiting incident with documented root cause and fix
- [HA Community: Pixoo 64 thread](https://community.home-assistant.io/t/divoom-pixoo-64/420660) — Community reports on device firmware behavior, buffer artifacts
- [MoonBench tiny pixel fonts](https://moonbench.xyz/projects/tiny-pixel-art-fonts/) — Font readability analysis for LED matrices at small sizes

### Tertiary (LOW confidence)
- [Divoom official API docs](http://doc.divoom-gz.com/web/#/12?page_id=196) — Official but sparse; did not load content during research; cross-validated via community sources
- [Pixel-Font-Gen for Pixoo](https://github.com/gickowtf/Pixel-Font-Gen) — Custom font generation tool; limited documentation

---
*Research completed: 2026-02-20*
*Ready for roadmap: yes*
