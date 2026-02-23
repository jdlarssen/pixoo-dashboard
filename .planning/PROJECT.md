# Divoom Hub

## What This Is

An always-on entryway dashboard running on a Divoom Pixoo 64 (64x64 LED pixel display). Displays time, Norwegian date, real-time bus departures from Ladeveien, and animated weather from Yr — everything you need before walking out the door. Custom PIL/Pillow rendering with BDF bitmap fonts, pushed to the device over LAN.

## Core Value

Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing — without pulling out your phone.

## Requirements

### Validated

- ✓ Full-frame custom rendering via PIL/Pillow pushed to Pixoo 64 (DISP-01) — v1.0
- ✓ Pixel font rendering with Norwegian character support æøå (DISP-02) — v1.0
- ✓ Single-screen layout — all info zones on 64x64 (DISP-03) — v1.0
- ✓ Auto-brightness based on time of day (DISP-04) — v1.0
- ✓ Display current time in large, readable digits (CLCK-01) — v1.0
- ✓ Display today's date in Norwegian (CLCK-02) — v1.0
- ✓ Show next bus departures from Ladeveien — direction 1 (BUS-01) — v1.0
- ✓ Show next bus departures from Ladeveien — direction 2 (BUS-02) — v1.0
- ✓ Countdown format for bus times (BUS-03) — v1.0
- ✓ Color coding by urgency green/yellow/red (BUS-04) — v1.0
- ✓ 60-second bus refresh cycle (BUS-05) — v1.0
- ✓ Current temperature from Yr/MET (WTHR-01) — v1.0
- ✓ Weather icon as pixel art sprite (WTHR-02) — v1.0
- ✓ Today's high/low temperature (WTHR-03) — v1.0
- ✓ Rain expected indicator (WTHR-04) — v1.0
- ✓ Connection refresh cycle to prevent 300-push lockup (RLBL-01) — v1.0
- ✓ Graceful error states with last known data (RLBL-02) — v1.0
- ✓ Auto-restart via launchd service wrapper (RLBL-03) — v1.0
- ✓ Push text message to temporarily override display via Discord (MSG-01) — v1.0
- ✓ Fix weather animation/rain text color indistinguishability (FARGE-01, FARGE-02, FARGE-03) — v1.1 Phase 7
- ✓ Comprehensive Norwegian README with full project documentation (DOC-01 through DOC-15) — v1.1 Phase 8
- ✓ "Built with Claude Code" transparency — badge and development process section (DOC-08) — v1.1 Phase 8

### Active

- [ ] Half-sun body at top-right of weather zone with radial ray emission (ANIM-01)
- [ ] Sun rays originate from sun and fade with distance (ANIM-02)
- [ ] Update sun body and ray tests for new geometry (ANIM-03)

### Out of Scope

- Mobile app — headless service pushing to Pixoo display, no UI needed
- Multi-device support — single Pixoo 64 in the entryway
- Historical data or logging — not useful for a glance-dashboard
- Native Pixoo text commands — can't coexist with custom rendering; no æøå support
- Route number display — only one bus route at Ladeveien
- Seconds display on clock — wastes pixels, minimal value for an entryway glance
- Offline mode — the display's value comes from live data

## Context

Shipped v1.0 with 3,767 LOC Python (2,321 src + 1,446 tests), 96 passing tests.
Tech stack: Python 3.12, PIL/Pillow, pixoo library, requests, discord.py.
Zone layout: clock 14px, date 9px, divider 1px, bus 19px, divider 1px, weather 20px = 64px.
APIs: Entur JourneyPlanner GraphQL (bus), MET Norway Locationforecast 2.0 (weather).
Bus stop: Ladeveien — NSR:Quay:73154 (Sentrum) and NSR:Quay:73152 (Lade/Strindheim).
Weather animations: rain, snow, sun, fog, thunder with 3D depth layering (bg/fg compositing around text).
Weather color issue fixed in v1.1 Phase 7. Norwegian README (414 lines) added in v1.1 Phase 8.

## Constraints

- **Display:** 64x64 pixels — every pixel matters for readability
- **APIs:** Open/free APIs only (Entur, MET Norway) — no paid services
- **Network:** Device and runtime on same LAN
- **Runtime:** Python 3.12 with pixoo library
- **Yr API terms:** User-Agent header and rate limits respected via If-Modified-Since caching

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single screen (no rotation) | All info at a glance without waiting | ✓ Good — validated by v1.0 layout |
| Norwegian language | User preference for date/day names | ✓ Good — manual dictionaries avoid locale dependency |
| Bus refresh 60s, weather 600s | Bus accuracy matters most; reduces API load | ✓ Good — timers coexist independently |
| Custom rendering over native Pixoo | Native can't do æøå or coexist with custom frames | ✓ Good — full control over every pixel |
| Python with pixoo library | Best Pixoo 64 library ecosystem | ✓ Good — draw_image() accepts PIL Image directly |
| BDF bitmap fonts (hzeller) | Confirmed æøå rendering in 4x6, 5x8, 7x13 | ✓ Good — all Norwegian characters verified |
| DisplayState equality for dirty flag | Only re-render when data changes | ✓ Good — efficient, prevents unnecessary device pushes |
| Zone pixel budget (14+9+1+19+1+20) | Tight but readable layout for all info zones | ✓ Good — confirmed readable at 2+ meters |
| Programmatic pixel art icons (not PNG) | 10px icons too small for file overhead | ✓ Good — 8 weather conditions with animations |
| Connection refresh every 300 pushes | Prevents device lockup discovered in research | ✓ Good — placed in Phase 1, prevented issues from day one |
| Discord bot for message override | User already uses Discord; thread-safe MessageBridge | ✓ Good — clean integration with lock-based thread safety |
| 3D depth animation system | bg/fg tuple composited around text for depth effect | ✓ Good — rain/snow particles pass through text naturally |
| Alpha values 65-150 for LED visibility | Original 15-50 invisible on physical hardware | ✓ Good — confirmed visible after compositing fix |
| Color fix: RGB only, no alpha changes | Alpha was empirically tuned in v1.0; preserve it | ✓ Good — vivid colors with preserved depth effect |
| Norwegian bokmaal with informal "du" tone | User preference; personal hobby project | ✓ Good — warm, approachable documentation |
| API docs in collapsible `<details>` blocks | Keep README scannable for new readers | ✓ Good — reference-heavy sections don't dominate |
| Safe placeholder values in README | Prevent personal data leakage (GPS, tokens, quay IDs) | ✓ Good — Oslo center coords, NSR:Quay:XXXXX |

## Completed Milestones

- **v1.0 MVP** — Shipped 2026-02-21. Full dashboard with clock, bus, weather, Discord override, birthday easter egg.
- **v1.1 Documentation & Polish** — Shipped 2026-02-21. Weather color fix (Phase 7) + comprehensive Norwegian README (Phase 8, 414 lines, 15 DOC requirements).

## Current Milestone: v1.2 Sun Ray Overhaul

**Goal:** Replace random sky-wide sun rays with radial beams that emit outward from a half-sun at the top-right of the weather zone.

**Target features:**
- Half-sun semicircle (radius 7) clipped at top edge of weather zone at x=48
- Rays emit radially from sun, fade with distance, respawn continuously
- Preserve two-depth-layer system (far/near) and yellow color palette

---
*Last updated: 2026-02-23 after v1.2 milestone start*
