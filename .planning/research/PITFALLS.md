# Pitfalls Research

**Domain:** Pixoo 64 entryway dashboard (LED pixel display with bus/weather data)
**Researched:** 2026-02-20
**Confidence:** MEDIUM (device API behavior verified across multiple community sources; API terms verified from official docs; some areas like Norwegian character support need hands-on validation)

## Critical Pitfalls

### Pitfall 1: Pixoo 64 Device Lockup After ~300 Push Calls

**What goes wrong:**
The Pixoo 64 stops responding entirely after approximately 300 screen updates via the HTTP API. The device becomes unresponsive and requires a power cycle to recover. Since this dashboard will be pushing updates every minute for bus times, you will hit this threshold within 5 hours of operation.

**Why it happens:**
The device firmware has an internal counter that appears to overflow or trigger a protection mechanism after ~300 consecutive `push()` / `Draw/SendHttpGif` calls. This is a firmware-level issue, not a network or software bug. Divoom has not fixed it.

**How to avoid:**
- Use the `refresh_connection_automatically` parameter (available in the `pixoo` Python library) which resets the internal counter every 32 frames at a slight performance cost.
- If building a custom client, implement a periodic connection reset cycle -- disconnect and reconnect the HTTP session every ~250 updates.
- Alternatively, use the device's native text/channel features where possible instead of full-frame image pushes, as these may not trigger the same counter.
- Never call `push()` more than once per second regardless -- the device also locks up from rapid-fire calls.

**Warning signs:**
- Device stops updating but does not show an error -- the last pushed frame remains frozen on screen.
- HTTP requests to the device start timing out.
- No error response from the device; it simply stops accepting connections.

**Phase to address:**
Core display engine phase. The very first integration with the Pixoo must include the connection refresh mechanism. Building without it means the dashboard dies overnight.

---

### Pitfall 2: Norwegian Characters (ae, oe, aa) Not Supported by Pixoo Native Fonts

**What goes wrong:**
The Pixoo 64's built-in `Draw/SendHttpText` command supports a limited character set: alphanumerics (0-9, a-z, A-Z) plus `!'()+,-<=>?[]^_:;./{|}~$@%`. Norwegian characters (ae, oe, aa) are not in this set. Additionally, certain font/character combinations crash the device entirely -- the device firmware has bugs where specific inputs cause a hard lock requiring power cycling.

**Why it happens:**
The Pixoo 64 was designed as a consumer gadget primarily for English/ASCII pixel art, not as a general-purpose text display. The 115 built-in fonts have inconsistent character sets, missing glyphs, and undocumented substitution behaviors (e.g., font 18 replaces `u`/`d` with arrow symbols; font 20 replaces `c`/`f` with degree symbols).

**How to avoid:**
- Do NOT rely on native `Draw/SendHttpText` for Norwegian text. Render text as pixel images in your application code using a known pixel font that includes Nordic characters, then push the rendered frame as an image.
- Use a bitmap font rendering approach: pick a 5x7 or similar pixel font with full Nordic character support, render it in Python/Node using PIL/Pillow or Canvas, and send the complete frame image.
- Test every font/character combination you plan to use before committing to a font -- some combinations crash the device.
- Keep a font test matrix during development to document which fonts are safe.

**Warning signs:**
- Missing characters appear as blank spaces, wrong symbols, or garbled output.
- Device crashes/freezes when certain text is sent -- especially with non-ASCII characters.
- Date display shows "tor 20. feb" correctly in English characters but ae/oe/aa render as garbage.

**Phase to address:**
Phase 1 (display foundation). This determines the entire rendering approach -- native text API vs. custom frame rendering. Must be decided before building any text display features. The decision cascades into everything: layout system, font choice, icon rendering.

---

### Pitfall 3: Yr API Banning Due to Missing/Bad Caching Implementation

**What goes wrong:**
The Yr (MET Norway) API will ban your IP address if you poll without proper HTTP caching. This is not a theoretical risk -- the Yr team explicitly states they receive weekly emails from developers who got blocked because they ignored caching requirements. Once banned, your weather display goes blank with no fallback.

**Why it happens:**
Developers implement naive polling loops (e.g., "fetch weather every 10 minutes") instead of implementing proper HTTP caching with `Expires` and `If-Modified-Since` headers. The Yr API is a free public service and enforces this strictly. Weather data for a specific location only updates 4 times per day for global forecasts, so polling every 10 minutes makes 144 redundant requests per day.

**How to avoid:**
- Implement full HTTP caching: store the `Expires` and `Last-Modified` headers from each response.
- Before making a new request, check if `current_time < expires_time`. If so, use cached data -- do NOT make a request.
- When cached data has expired, include `If-Modified-Since` header. Accept `304 Not Modified` as a valid "use cached data" response.
- Truncate coordinates to 4 decimal places maximum (e.g., `lat=63.4305&lon=10.3951` for Trondheim). More precision breaks API caching and returns 400 errors.
- Set a proper `User-Agent` header with your app name (e.g., `divoom-hub/1.0 github.com/user/divoom-hub`). Missing or generic User-Agent returns 403 Forbidden.
- Use HTTPS -- HTTP requests get throttled.

**Warning signs:**
- 403 Forbidden responses (missing User-Agent).
- 429 Too Many Requests (polling too frequently).
- 400 Bad Request (coordinate precision too high).
- Weather data suddenly stops updating after days of working fine (IP banned).

**Phase to address:**
Weather integration phase. The HTTP caching layer must be built as a proper module, not bolted on after the fact. Design the weather fetcher around the cache-first pattern from day one.

---

### Pitfall 4: Entur API Rate Limiting With Shared Client Names

**What goes wrong:**
The Entur API rate-limits based on the `ET-Client-Name` header. If you use a generic or commonly-used client name, your requests get lumped together with other consumers using the same name, and you hit rate limits even with modest polling. This was a documented issue in the Home Assistant community where all HA instances shared the same client identifier, causing widespread 429 errors.

**Why it happens:**
Entur applies "strict rate-limiting policies on API-consumers who do not identify with a header" and uses the client name for per-consumer tracking. The default policy (for consumers without a formal Entur agreement) has undocumented but real limits. Polling every 45 seconds is the practical minimum used by production integrations.

**How to avoid:**
- Always include the `ET-Client-Name` header. Format: `company-application` (e.g., `jdl-divoomhub`).
- Include a unique identifier component if possible (the Home Assistant fix was to hash the instance URL into a UUID).
- Poll no more frequently than every 45-60 seconds for departure data.
- Cache responses and only re-fetch when needed.
- Use Quay IDs (specific platform) rather than StopPlace IDs (entire stop area) to get direction-specific departures, reducing the amount of data filtering needed client-side.

**Warning signs:**
- HTTP 429 responses from `api.entur.io`.
- Bus departure data stops updating while weather data continues working.
- Intermittent gaps in departure data during peak hours.

**Phase to address:**
Bus data integration phase. The Entur client must be built with proper identification and rate limiting from the first request.

---

### Pitfall 5: Cramming Too Much Information Into 64x64 Pixels

**What goes wrong:**
Developers try to display time, date, 4 bus departures (line number, time, direction for each), temperature, weather icon, high/low, and rain indicator all on a single 64x64 screen. At 5x7 pixel fonts (the minimum readable size), a single character is already ~8% of the display width. The result is unreadable at a glance -- which defeats the entire purpose of an entryway dashboard.

**Why it happens:**
64x64 sounds like "enough pixels" until you do the math. At a readable 5-pixel-wide font with 1-pixel spacing, you get roughly 10 characters per line and 8 lines of text. That is the absolute maximum, and it leaves zero room for spacing, icons, or visual hierarchy. Most dashboard projects iterate 3-5 times on layout before finding something that works.

**How to avoid:**
- Do the pixel math first. Map out every element with exact pixel dimensions before writing code.
- Prioritize ruthlessly: clock gets the most space (it is the most-glanced element), bus times get the next most, weather gets compact representation.
- Use abbreviations aggressively: "6" not "Linje 6", time as "3m" not "14:23".
- Weather icon should be small pixel art (8x8 or 12x12 max), not a large graphic.
- High/low temperature can be tiny (e.g., "2/8" in small font).
- Consider a 2-3 zone layout: top zone (time/date), middle zone (bus departures), bottom zone (weather). Strict zone boundaries prevent sprawl.
- Build a pixel-perfect mockup tool or use graph paper before touching the display.

**Warning signs:**
- Text overlaps or characters bleed into adjacent elements.
- You need a magnifying glass to read the display from more than 1 meter away.
- Layout changes require rewriting multiple components because everything is tightly coupled.
- Constant "just one more pixel" adjustments that break other elements.

**Phase to address:**
Layout design phase (should be early, before individual data integrations). Define zones and pixel budgets before implementing any data display. The layout is the architecture of this project.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using native `Draw/SendHttpText` for all text | Faster to implement, no font rendering code | Cannot display Norwegian characters, crash risk with certain fonts, no control over rendering quality | Never for this project -- Norwegian text is a core requirement |
| Polling APIs on fixed intervals instead of respecting cache headers | Simpler code, no cache management | API bans from Yr, rate limiting from Entur, wasted network traffic | Never -- both APIs enforce this |
| Hardcoding stop IDs and coordinates | Works immediately for Ladeveien | Breaks if stops are renumbered (Entur NSR updates), impossible to test with other locations | Acceptable for MVP if IDs are in config, not buried in code |
| No error handling on API failures | Simpler code path | Display shows stale data with no indication, or crashes on network errors | Never -- network failures are guaranteed on a LAN device |
| Full-frame image push for every update | Simplest rendering model | Hits the 300-push lockup faster, more bandwidth per update | Only acceptable if connection refresh mechanism is in place |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Pixoo 64 HTTP API | Calling `push()` more than once per second | Throttle all push calls to minimum 1-second intervals; implement a queue if multiple components want to update |
| Pixoo 64 HTTP API | Sending image before clearing buffer | Always clear the buffer before drawing a new frame; otherwise previous frame pixels bleed through |
| Pixoo 64 HTTP API | Using `Draw/CommandList` to batch animation frames | `CommandList` cannot batch frames; must use sequential `Draw/SendHttpGif` calls. Each call blocks during transmission |
| Yr Locationforecast | Using 6+ decimal places in coordinates | Truncate to max 4 decimals. More precision harms cache performance and may return 400 errors |
| Yr Locationforecast | Treating `symbol_code` and precipitation as instant data | These are period aggregations (`next_1_hours`, `next_6_hours`). Temperature is instant. They live in different JSON paths |
| Yr Locationforecast | Not handling `203` status code | 203 means the product is deprecated or beta. Still works but should trigger a warning/log for future migration |
| Yr Locationforecast | All timestamps are UTC | Must convert to local Norwegian time (CET/CEST) for display. Use timezone-aware datetime handling, not naive offsets |
| Entur GraphQL | Querying StopPlace when you need direction-specific data | Query specific Quay IDs to get departures for one direction. StopPlace returns all directions mixed together |
| Entur GraphQL | Not including `ET-Client-Name` header | Mandatory. Format: `company-application`. Without it, strict rate limiting applies immediately |
| Entur GraphQL | Assuming real-time data is always available | `monitored` field indicates if departure is real-time or schedule-based. Real-time coverage is inconsistent and has temporary gaps |
| Entur GraphQL | Using v2 API | v2 was EOL'd and broke existing installations. Use v3 exclusively: `api.entur.io/journey-planner/v3/graphql` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full frame redraw every update cycle | High CPU on host, unnecessary push calls to Pixoo, faster approach to 300-push lockup | Only redraw when data actually changes. Compare new data to cached data before triggering a frame push | Within hours of continuous operation |
| Loading animation on every frame send | 5+ second "Loading.." animation plays on device before each update, making display unusable for real-time info | Use `Draw/SendHttpGif` with static frames or use native channel features to avoid the loading animation | Immediately -- every update shows a loading spinner |
| Animation frames exceeding 40-frame limit | Device crashes or freezes | Keep animations under 40 frames. For a dashboard, animations are unnecessary -- use static frames only | Immediately upon exceeding limit |
| Polling Entur every 30 seconds | 429 rate limit responses, eventual blocking | Poll every 60 seconds minimum. Cache responses. The bus schedule does not change faster than this | After several hours of operation, or sooner if Entur is under load |
| Rendering images at high resolution then downscaling | Blurry, aliased text and icons on the 64x64 grid | Render at exactly 64x64 pixels. Every pixel must be intentional. No antialiasing -- it makes LED pixels look muddy | Immediately visible as poor display quality |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing Pixoo device IP on the internet | Device has no authentication -- anyone can push content to it | Keep the Pixoo on a LAN-only network segment. The dashboard service and Pixoo must be on the same LAN, but neither should be internet-accessible |
| Storing API credentials in source code | Not applicable here (all APIs are open/free), but Divoom remote API requires login with MD5-hashed password | Stick to the local HTTP API which requires no authentication. Do not use the remote `appin.divoom-gz.com` API |
| Not blocking Pixoo telemetry | Device phones home to `rongcfg.com` and `rongnav.com` (telemetry) and connects to Divoom's MQTT server | If privacy matters, block these domains via DNS/firewall. Not critical for functionality but worth knowing |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Using scrolling text for bus times | User has to wait for text to scroll past to read it -- defeats "glance and go" purpose | Static text positioned in fixed zones. If text doesn't fit, abbreviate more aggressively |
| Showing absolute departure times (e.g., "14:23") instead of relative ("3 min") | Requires mental math to determine if you can catch the bus | Show relative minutes for departures within 20 min, absolute time for departures further out |
| No visual distinction between bus directions | User can't tell which direction a departure goes | Use spatial separation (left column = direction 1, right column = direction 2) or color coding |
| Weather icon too large | Steals pixels from more critical bus/time info | 8x8 pixel weather icon is sufficient. Weather is supplementary info, not primary |
| No staleness indicator | User trusts stale data if API fails and display shows last-fetched times | Dim the display, show a small warning pixel, or flash a status indicator when data is older than 2 minutes |
| Clock not prominent enough | The most-glanced element is hard to read | Clock should use the largest font on the display, positioned where the eye naturally lands first (top or center) |
| Trying to show "bus line name + destination + time" for each departure | Takes 20+ characters per line, impossible at readable font sizes | Show only line number and minutes until departure (e.g., "6 3m") |

## "Looks Done But Isn't" Checklist

- [ ] **Bus departures:** Shows real-time data but falls back silently to schedule data when real-time is unavailable -- verify the `monitored` field is checked and displayed appropriately
- [ ] **Weather caching:** Fetches data successfully but does not respect `Expires` header -- verify with network logging that redundant requests are not being made
- [ ] **Pixoo connection:** Display updates work but no connection refresh mechanism -- verify the dashboard survives 6+ hours of continuous operation without freezing
- [ ] **Timezone handling:** Times display correctly in summer (CEST, UTC+2) but wrong in winter (CET, UTC+1) or vice versa -- verify with both timezone offsets
- [ ] **Error recovery:** Dashboard works when all APIs are up but crashes or shows blank screen when any single API is down -- verify each API failure independently
- [ ] **WiFi recovery:** Dashboard works after boot but does not reconnect to Pixoo after a brief WiFi dropout -- verify by temporarily disconnecting WiFi and reconnecting
- [ ] **Norwegian date:** Date shows correctly for most days but fails on months or days with ae/oe/aa characters -- verify: "mandag", "tirsdag", "onsdag" (all fine) vs "lordag" (needs oe), "mars" (fine) vs "februar" (fine), "aste" (needs ae)
- [ ] **Night/day weather icons:** Weather icon shows daytime variant at night because `symbol_code` includes `_day`/`_night`/`_polartwilight` suffixes that must be handled
- [ ] **Coordinate precision:** API works in development but fails in production because geocoding service returned 8-decimal coordinates -- verify coordinates are truncated to 4 decimals

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Pixoo 300-push lockup | LOW | Power cycle the device (unplug/replug USB). Add connection refresh mechanism to prevent recurrence |
| Yr API IP ban | MEDIUM | Wait for ban to expire (duration unknown). Implement proper caching. May need to contact met.no support if ban persists |
| Entur 429 rate limiting | LOW | Reduce polling frequency, add unique client identifier. Rate limits lift automatically once traffic normalizes |
| Norwegian character crash | LOW | Avoid native text API. Switch to image-based text rendering. Requires architectural change if native text was used throughout |
| Layout too cramped | MEDIUM | Requires redesign of the pixel grid layout. If rendering code is tightly coupled to layout coordinates, this cascades into multiple files |
| Stale data displayed as fresh | LOW | Add timestamp tracking to each data source. Display staleness indicator. Architectural fix, not a data fix |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Pixoo 300-push lockup | Phase 1: Device connectivity | Run display for 8+ hours continuously. Verify no freezes. Check push counter in logs |
| Norwegian character rendering | Phase 1: Display foundation | Render "lordag 21. mars" on display. Verify ae and oe characters render correctly |
| Yr API caching/banning | Phase 2: Weather integration | Monitor network traffic for 24 hours. Verify no redundant API calls. Check `If-Modified-Since` headers are sent |
| Entur rate limiting | Phase 2: Bus data integration | Run for 24 hours. Verify no 429 responses in logs. Confirm `ET-Client-Name` header in all requests |
| Layout cramming | Phase 1: Layout design | View display from 2 meters away. All primary info (time, next bus) must be readable without squinting |
| Stale data display | Phase 3: Error handling | Kill network connection for 5 minutes. Verify display shows staleness indication. Restore and verify recovery |
| Timezone errors | Phase 2: Data integration | Test with mocked UTC times for both CET and CEST. Verify correct local times displayed |
| WiFi reconnection | Phase 3: Reliability | Disconnect WiFi for 30 seconds. Verify dashboard reconnects to Pixoo and resumes updates within 60 seconds |
| Buffer ghosting | Phase 1: Display engine | Push 10 different frames rapidly. Verify no artifacts from previous frames remain visible |

## Sources

- [SomethingWithComputers/pixoo Python library](https://github.com/SomethingWithComputers/pixoo) -- MEDIUM confidence: community library, well-maintained, documents device behavior from extensive testing
- [Grayda/pixoo_api NOTES.md](https://github.com/Grayda/pixoo_api/blob/main/NOTES.md) -- MEDIUM confidence: detailed reverse-engineering notes on Pixoo API, covers undocumented behavior
- [Yr Developer Getting Started](https://developer.yr.no/doc/GettingStarted/) -- HIGH confidence: official MET Norway API documentation
- [Yr Locationforecast HowTo](https://developer.yr.no/doc/locationforecast/HowTO/) -- HIGH confidence: official usage guide with coordinate and caching rules
- [Yr Locationforecast Data Model](https://docs.api.met.no/doc/locationforecast/datamodel.html) -- HIGH confidence: official data structure documentation
- [Yr Locationforecast FAQ](https://docs.api.met.no/doc/locationforecast/FAQ.html) -- HIGH confidence: official FAQ covering update frequency and common mistakes
- [Entur Developer Docs](https://developer.entur.org/pages-intro-getstarted/) -- HIGH confidence: official Entur API documentation
- [Entur Rate Limit Issue in Home Assistant](https://github.com/home-assistant/core/issues/86547) -- MEDIUM confidence: real-world rate limit incident with fix documentation
- [hfurubotten/enturclient](https://github.com/hfurubotten/enturclient) -- MEDIUM confidence: Python client showing practical API usage patterns
- [MMM-Entur-tavle](https://github.com/Arve/MMM-Entur-tavle) -- MEDIUM confidence: working MagicMirror departure board noting v2 EOL
- [Entur Stop/Quay ID Guide](https://github.com/ringvold/pidash/wiki/How-to-find-stop-and-quay-ids-for-the-Entur-API) -- MEDIUM confidence: practical guide for ID discovery
- [Home Assistant Pixoo 64 Community Thread](https://community.home-assistant.io/t/divoom-pixoo-64/420660) -- LOW confidence: community reports, anecdotal but consistent patterns
- [Divoom Help Center](https://divoom.com/apps/help-center) -- MEDIUM confidence: official but consumer-focused, not developer-focused

---
*Pitfalls research for: Pixoo 64 entryway dashboard (Trondheim bus + weather)*
*Researched: 2026-02-20*
