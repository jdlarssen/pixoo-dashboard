# Feature Landscape

**Domain:** Entryway information dashboard on Divoom Pixoo 64 (64x64 LED pixel display)
**Researched:** 2026-02-20

## Pixoo 64 Native vs Custom Rendering

Understanding what the device does natively is critical before deciding what to build custom.

### Native Capabilities (via Divoom app / built-in firmware)

| Capability | How It Works | Limitations | Confidence |
|-----------|--------------|-------------|------------|
| Clock faces | Hundreds available via Divoom app; set via API `set_clock(id)` | Cannot combine with custom data overlays; it is the full 64x64 display | HIGH |
| Weather display | Built-in via Divoom app; uses OpenWeatherMap; location auto-synced or manual | Fixed layout, cannot customize what data shows; uses Divoom's own weather source (not Yr) | HIGH |
| Social stats counters | YouTube, Twitter, Twitch follower counts | Irrelevant for this project | HIGH |
| Crypto/stock tickers | Built-in finance displays | Irrelevant for this project | HIGH |
| Audio visualizer | EQ/spectrum display using built-in mic | Irrelevant for this project | HIGH |
| Custom channels (3 slots) | Save images/animations to device memory; work offline | Static content only; no live data | HIGH |
| Scrolling text | API `Draw/SendHttpText` with font, position, speed, direction | Text can only scroll left with most fonts; limited font options; cannot mix with pixel-buffer rendering | MEDIUM |
| Brightness control | API `Channel/SetBrightness` (0-100) | Works well, no issues reported | HIGH |
| Screen on/off | API `set_screen(on/off)` | Works well | HIGH |
| GIF playback | Play from URL, local storage, or gallery | Up to ~40 frames before device crashes | HIGH |

### What MUST Be Custom-Rendered

For this project's requirements (time + date + bus departures + weather from Yr, all on one screen), **virtually everything must be custom-rendered** because:

1. **Native clock faces occupy the entire 64x64 screen** -- you cannot overlay bus times or weather on top of a native clock face.
2. **Native weather uses OpenWeatherMap**, not Yr (which is required for Norwegian weather data accuracy and API terms).
3. **Native text scrolling (`SendHttpText`) cannot coexist with pixel-buffer rendering** (`SendHttpGif`) -- they are separate display modes. You use one or the other.
4. **There is no native bus/transit display** -- this must be fetched from ATB's API and rendered.
5. **The only way to show multiple data types on one screen** is to compose a full 64x64 pixel image and send it via `Draw/SendHttpGif`.

**Verdict:** Use `Draw/SendHttpGif` (full-frame pixel buffer) for the dashboard. Render the entire 64x64 image server-side (using PIL/Pillow or similar), then push the base64-encoded RGB data to the device. This is the approach used by pixoo-weather, the Home Assistant integration's "components" mode, and every serious custom dashboard project.

The only native features worth using are:
- **Brightness control** -- use the API to auto-dim at night
- **Screen on/off** -- turn off at bedtime, on in the morning

## Table Stakes

Features the user expects. Missing = the dashboard is useless as an entryway display.

| Feature | Why Expected | Complexity | Rendering | Notes |
|---------|--------------|------------|-----------|-------|
| Current time (large, readable) | Core purpose -- glance at time before leaving | Low | Custom (full-frame) | Must be the dominant visual element; use a large pixel font (likely 5x7 or larger for digits). Time must update every minute at minimum. |
| Today's date in Norwegian | Context for "what day is it?" before leaving | Low | Custom (full-frame) | Format: "tor 20. feb" -- short day name + date + short month. Requires a compact font (3x5 or 4x6). Norwegian locale strings are trivial to implement (12 months, 7 days). |
| Next 2 bus departures (direction 1) | Core purpose -- "when do I need to leave?" | Medium | Custom (full-frame) | Show route number + minutes until departure. ATB API (EnTur/national API) provides real-time data. Must refresh every 60 seconds. Show "naa" or similar when bus is imminent. |
| Next 2 bus departures (direction 2) | Same as above, opposite direction | Medium | Custom (full-frame) | Same format. Two directions means 4 departure lines total. This is 4 compact data rows. |
| Current temperature | "Do I need a jacket?" | Low | Custom (full-frame) | Yr API. Display as e.g. "-3" or "12" with degree symbol. Large enough to read at a glance. |
| Weather icon | Instant visual weather status | Medium | Custom (full-frame) | Must design pixel art icons for sun, cloud, rain, snow, etc. Yr provides weather symbol codes. A 10x10 to 16x16 pixel icon area is reasonable. |
| Single-screen layout (no rotation) | User requirement -- all info visible at a glance | High | Custom (full-frame) | This is the hardest constraint. 64x64 pixels must fit: time, date, 4 bus departures, temperature, weather icon. Layout design is THE critical challenge. |
| Auto-refresh (bus: 1min, weather: 10-15min) | Data must be current to be useful | Low | N/A (backend logic) | Bus data refreshes every 60s. Weather every 10-15 minutes (Yr rate limit friendly). Clock updates every 60s (or on the minute). |

## Differentiators

Features that make this dashboard notably better than a basic setup. Not required for MVP, but high value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rain expected indicator | "Should I grab an umbrella?" -- immediate visual cue | Low | Yr provides precipitation forecast. A single colored pixel/icon or "!" indicator near weather. Tiny addition, huge practical value. |
| Today's high/low temperature | Context for dressing decisions beyond current temp | Low | Yr API provides daily min/max. Display as small text like "H5 L-2" near current temp. |
| Auto-brightness (night dimming) | Avoid blinding LED glare in dark hallway at night | Low | Use `Channel/SetBrightness` API on a schedule. Trivially easy and highly practical for an always-on display. |
| Custom push message | Temporary message overlay (e.g., "HUSK NØKLER" / "remember keys") | Medium | Would require an HTTP endpoint or MQTT listener on the server that temporarily overrides the dashboard. Useful but requires designing the override mechanism. |
| Bus departure countdown coloring | Color-code departures: green (plenty of time), yellow (hurry), red (missed) | Low | Simple conditional: >10 min = green, 3-10 min = yellow, <3 min = red. Immediately readable without parsing numbers. |
| Graceful error states | Show clear indicators when API is down instead of stale data | Medium | Display a small warning icon or "?" when bus/weather API fails. Stale data with no indicator is worse than showing "offline". |
| Screen schedule (on/off times) | No point showing data at 2 AM; saves power and reduces LED wear | Low | Cron-like schedule using `set_screen()` API. e.g., on at 06:00, off at 23:00. |
| Weekend/weekday mode | Different display on weekends (no bus times needed, show more weather) | Medium | Conditional layout based on day of week. Reclaims pixels on weekends for larger weather display. |
| Smooth minute transitions | Avoid the "blink" when refreshing the display | Medium | Known Pixoo issue: buffer artifacts when pushing new frames. Can mitigate by sending frames at controlled intervals and avoiding rapid pushes (max 1 push/second). |

## Anti-Features

Features to deliberately NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Native Divoom clock faces | Occupy the full screen; cannot overlay custom data; would lose bus/weather info | Render custom time display as part of the full-frame image |
| Native Divoom weather | Uses OpenWeatherMap (not Yr); fixed layout; cannot combine with bus data | Fetch from Yr API and render custom |
| Scrolling text for data display | `SendHttpText` cannot coexist with full-frame `SendHttpGif` rendering; scrolling text is distracting for always-on display; limited font options | Render static text as pixels in the frame buffer |
| Animated transitions/effects | 64x64 is too small for animation to add value; animations increase complexity; max ~40 frames before device crashes; each push must be >1 second apart | Static frames, updated on refresh interval |
| Multi-page rotation | User explicitly wants single-screen -- all info at a glance without waiting for rotation | Fit everything on one 64x64 layout |
| Complex pixel art decoration | Every pixel matters for data; decorative borders/icons eat into the limited space | Minimal chrome, maximum information density |
| Mobile app / web UI for config | Out of scope per project definition; adds massive complexity | Config file or environment variables |
| Historical data / logging | Out of scope; adds storage requirements and complexity | Display only current/upcoming data |
| Multi-device support | Only one Pixoo 64 | Hardcode single device IP |
| Real-time second display | Updating every second wastes device bandwidth (max 1 push/sec); seconds are not useful for an entryway display | Update every 60 seconds, on the minute |

## Layout Analysis: What Fits on 64x64

This is the most critical design constraint. Based on research into pixel font sizes and existing Pixoo 64 projects:

### Font Size Reality on 64x64

| Font Size | Character Dimensions | Readability | Best For | Fits Per Row (64px) |
|-----------|---------------------|-------------|----------|---------------------|
| 3x5 (+ 1px gap) | 4px wide per char | Readable but small; some characters ambiguous (G/C, 0/O) | Secondary info: date, labels | ~16 characters |
| 4x6 (+ 1px gap) | 5px wide per char | Good readability; most characters distinct | Bus times, temperatures | ~12 characters |
| 5x7 (+ 1px gap) | 6px wide per char | Very readable; clear at a distance | Time display digits | ~10 characters |
| 7x9+ | 8px wide per char | Excellent; visible across room | Large clock display | ~8 characters |

### Proposed Layout Budget (64x64 pixels)

```
Row allocation (top to bottom):
+----------------------------------+  y=0
|  TIME (large)        WEATHER ICN |  ~16px tall (large digits + icon)
|  13:45               [sun icon]  |
+----------------------------------+  y=16
|  tor 20. feb            -3°      |  ~8px tall (date + temp)
+----------------------------------+  y=24
|  H: 5°  L: -1°    [rain icon]   |  ~8px tall (high/low + rain indicator)
+----------------------------------+  y=32
|  --- BUS RETNING 1 ---           |  ~6px (section label, optional)
|  6  3min   6  18min              |  ~8px (two departures)
+----------------------------------+  y=46
|  --- BUS RETNING 2 ---           |  ~6px (section label, optional)
|  6  7min   6  22min              |  ~8px (two departures)
+----------------------------------+  y=60
|  [4px padding/status area]       |
+----------------------------------+  y=64
```

This is approximate and will need iteration. Key constraints:
- Time must be the largest element (10-16px tall digits)
- Bus departures need route number + minutes, compact but readable
- Weather icon needs at least 10x10 pixels to be recognizable
- 1px gaps between sections prevent visual bleed on LEDs

### What Existing Projects Teach Us

| Project | Approach | Key Lesson |
|---------|----------|------------|
| pixoo-weather | PIL/Pillow image generation with 3x5 pixel font, sent as GIF | Small fonts work; GIF approach is standard; refresh every 1 min |
| Node-RED pixoo-dash | 20 fields, 7 chars each, 4 blocks | Structured grid works but text-only is limiting |
| Home Assistant integration | PIL-based compositing with multiple element types | Components model (text + images + shapes) is the most flexible |
| HA community projects | Single-purpose displays (one notification at a time) | Dense multi-data layouts are hard but possible with careful design |

## Feature Dependencies

```
Core rendering pipeline (PIL/Pillow + SendHttpGif)
  |
  +-> Time display (requires: font rendering, minute-based refresh loop)
  |     +-> Date display (requires: Norwegian locale strings)
  |
  +-> Bus departures (requires: ATB/EnTur API client, refresh scheduler)
  |     +-> Departure countdown coloring (requires: bus departures working)
  |
  +-> Weather display (requires: Yr API client, weather icon sprites)
  |     +-> Current temperature
  |     +-> Weather icon
  |     +-> High/low temperatures (requires: daily forecast parsing)
  |     +-> Rain indicator (requires: precipitation forecast)
  |
  +-> Layout engine (requires: all data sources + font rendering)
        +-> Single-screen compositor (combines all elements at coordinates)

Device connectivity (requires: Pixoo 64 on LAN, discovered IP)
  +-> Brightness control
  +-> Screen schedule
  +-> Push frame to display

Custom push message (requires: HTTP server or message listener + display override logic)
```

## MVP Recommendation

**Phase 1: Core rendering pipeline + time/date**
1. PIL/Pillow image generation at 64x64
2. Custom pixel font rendering (3x5 and 5x7 minimum)
3. Time display (large digits)
4. Date display (Norwegian, compact)
5. Push to Pixoo via `Draw/SendHttpGif`
6. Minute-based refresh loop

**Phase 2: Bus departures**
1. ATB/EnTur API client
2. Parse next 2 departures per direction
3. Render in layout below time/date
4. 60-second refresh cycle

**Phase 3: Weather**
1. Yr API client (with proper User-Agent)
2. Current temperature display
3. Weather icon sprites (pixel art, ~12x12)
4. High/low temperatures
5. Rain indicator

**Phase 4: Polish and differentiators**
1. Auto-brightness / screen schedule
2. Bus countdown coloring
3. Graceful error states
4. Custom push messages

**Defer:** Weekend mode, animated transitions, complex decorations. These add complexity without proportional value. The display should be rock-solid before adding conditional layouts.

## Rendering Approach Recommendation

**Use PIL/Pillow to generate the full 64x64 image server-side, then push as a single frame via `Draw/SendHttpGif`.** This is the proven approach used by every serious Pixoo 64 dashboard project. It gives complete control over:
- Pixel-precise layout
- Custom bitmap fonts at any size
- Weather icon sprites
- Color per-pixel
- No dependency on Divoom's limited built-in text rendering

The alternative (using Divoom's `SendHttpText` for text + native features) is a dead end because text mode and pixel-buffer mode cannot coexist on the same display.

## Sources

- [SomethingWithComputers/pixoo](https://github.com/SomethingWithComputers/pixoo) - Primary Python library for Pixoo 64 (PICO-8 font, draw methods, push buffer) -- HIGH confidence
- [Grayda/pixoo_api NOTES.md](https://github.com/Grayda/pixoo_api/blob/main/NOTES.md) - Comprehensive reverse-engineered API command list -- HIGH confidence
- [pixoo-weather](https://github.com/jankornfeld/pixoo-weather) - Weather display project using PIL + 3x5 font + GIF approach -- MEDIUM confidence
- [pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant) - Home Assistant integration with components/compositing model -- HIGH confidence
- [Node-RED pixoo-dash](https://flows.nodered.org/node/@nickiv/node-red-pixoo-dash) - Structured text grid approach (20 fields, 7 chars) -- MEDIUM confidence
- [Divoom Pixoo 64 product page](https://divoom.com/products/pixoo-64) - Native feature overview -- HIGH confidence
- [Divoom Pixoo 64 MakeUseOf review](https://www.makeuseof.com/divoom-pixoo-64-review/) - Native channels and customization details -- MEDIUM confidence
- [HA Community: Pixoo 64 projects](https://community.home-assistant.io/t/divoom-pixoo-64/420660) - Real-world dashboard experiences and limitations -- MEDIUM confidence
- [HA Blueprint: Send Text 4 Lines](https://community.home-assistant.io/t/divoom-pixoo64-send-text-4-lines/554428) - Text layout coordinates (font 8, y-spacing of 15px) -- MEDIUM confidence
- [Pixoo 64 Tools DeepWiki](https://deepwiki.com/itsmikethetech/Pixoo-64-Tools) - Rendering pipeline details (PIL + scaling + push) -- MEDIUM confidence
- [MoonBench tiny pixel fonts](https://moonbench.xyz/projects/tiny-pixel-art-fonts/) - Font readability analysis (3x3 min, 3x5 good, 5x5 ideal) -- HIGH confidence
- [Pixel-Font-Gen for Pixoo](https://github.com/gickowtf/Pixel-Font-Gen) - Custom font generation tool for Pixoo 64 -- LOW confidence (limited docs)
- [pixoo PyPI](https://pypi.org/project/pixoo/) - Python library details, PICO-8 font, buffer model -- HIGH confidence
- [Kickstarter Pixoo 64 FAQ](https://www.kickstarter.com/projects/divoom/pixoo-64-the-pixel-art-smart-clock-for-the-cyber-world/faqs) - Native channel details, custom channel limits (3 slots, 100+ items) -- MEDIUM confidence
- [Divoom official API docs](http://doc.divoom-gz.com/web/#/12?page_id=196) - Official API reference (ShowDoc platform, requires JS rendering) -- LOW confidence (page did not load content)
