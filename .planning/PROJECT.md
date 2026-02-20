# Divoom Hub

## What This Is

An entryway dashboard running on a Divoom Pixoo 64 (64x64 LED pixel display). Shows time, date, bus departures, and weather at a glance — everything you need before walking out the door. Designed for readability on an extremely constrained pixel canvas.

## Core Value

Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing — without pulling out your phone.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Display current time (readable at a glance)
- [ ] Display today's date in Norwegian (e.g. "tor 20. feb")
- [ ] Show next 2 bus departures from Ladeveien — direction 1
- [ ] Show next 2 bus departures from Ladeveien — direction 2
- [ ] Show current temperature (°C) from Yr
- [ ] Show weather icon (sun, clouds, rain, etc.) as pixel art
- [ ] Show today's high/low temperature
- [ ] Show rain expected indicator
- [ ] All info on a single 64x64 screen — readable, not cramped
- [ ] Bus times refresh every minute
- [ ] Weather refreshes at a sensible lower interval
- [ ] Custom message capability (push text to display — details TBD)
- [ ] Research Pixoo 64 native capabilities vs custom rendering (use what the device does well natively)

### Out of Scope

- Mobile app — this is a headless service pushing to the display
- Multi-device support — one Pixoo 64
- Historical data or logging
- Complex animations — readability over flash

## Context

- **Device:** Divoom Pixoo 64 — 64x64 RGB LED pixel display, controlled over LAN via HTTP API
- **Bus data:** ATB open API (atb.no) — public transit for Trøndelag. Stop: Ladeveien, both directions.
- **Weather data:** Yr open API (yr.no) — Norwegian Meteorological Institute. Location: Trondheim.
- **Display language:** Norwegian
- **Pixel UX is critical:** 64x64 is extremely constrained. Font choice, icon design, layout, and spacing need careful research and iteration. This is a first-class design concern, not an afterthought.
- **Device not yet on network** — setup will happen during implementation
- **The Pixoo 64 has native features** (built-in clock faces, channels, etc.) — research needed to determine what to use natively vs what to render custom

## Constraints

- **Display:** 64x64 pixels — every pixel matters for readability
- **APIs:** Must use open/free APIs (ATB, Yr) — no paid services
- **Network:** Device and runtime on same LAN
- **Runtime:** TBD — research will determine best approach (Python vs Node.js vs other)
- **Yr API terms:** Must include proper User-Agent header and respect rate limits

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single screen (no rotation) | User wants all info at a glance without waiting | — Pending |
| Norwegian language | User preference for date/day names | — Pending |
| Bus refresh every 1 min, weather less often | Bus accuracy matters most; reduces API load | — Pending |
| Research native Pixoo features first | Don't rebuild what the device does well | — Pending |
| Runtime TBD | Depends on Pixoo library ecosystem | — Pending |

---
*Last updated: 2026-02-20 after initialization*
