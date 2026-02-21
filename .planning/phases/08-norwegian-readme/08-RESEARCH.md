# Phase 8: Norwegian README - Research

**Researched:** 2026-02-21
**Domain:** Technical documentation (Norwegian bokmaal README for a Python/Pillow IoT dashboard)
**Confidence:** HIGH

## Summary

Phase 8 is a pure documentation phase -- no code changes, only creating a comprehensive Norwegian-language README.md. The codebase is a ~2,350 LOC Python project that drives a Pixoo 64 LED display as an always-on home dashboard showing clock, bus departures (Entur API), and weather (MET Norway API) with animated overlays, Discord message override, and a birthday easter egg.

The research focused on: (1) cataloguing every technical detail from the actual source code so the planner can produce accurate documentation plans, (2) identifying README structure best practices for hobby/personal projects, and (3) understanding shields.io badge conventions for the "Bygget med Claude Code" requirement.

**Primary recommendation:** Structure the README as a single file with clear sections flowing from "what is this?" through "how to install/run" to "how does it work technically", written in warm/personal Norwegian bokmaal that reflects the hobby project nature.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Written in bokmaal (Norwegian bokmal)
- Personal touch -- acknowledge this is a personal home dashboard project, adds warmth and context
- Zone layout diagram: both a conceptual ASCII overview for quick understanding AND a reference table with exact pixel coordinates
- Display photo: ASCII art representation of the Pixoo 64 display showing the zones PLUS an image placeholder tag for a real photo the user will add later
- "Bygget med Claude Code" badge near the top of README
- AI development transparency section explaining how Claude Code was used
- Emoji usage: minimal -- a few key ones where they aid scanning, but mostly clean text headers
- User wants to add their own display photo later -- include a working image placeholder that gracefully shows alt text until the real photo is added
- The ASCII art should simulate what the actual Pixoo 64 display looks like with all zones active
- Bokmaal specifically, not nynorsk
- Personal project framing -- this is someone's home dashboard, not a corporate product

### Claude's Discretion
- Register and formality level: pick what reads naturally for a hobby project README
- Section ordering, depth per section, collapsible vs expanded, single file vs split docs: optimize for reading experience
- Code examples detail level: balance based on each section's complexity
- .env placeholder style: pick safe, clear placeholder values -- no real personal data
- Badge link target, section tone, detail depth, inclusion of stats
- Overall register and formality of Norwegian writing
- Technical term handling (English vs norwegianized)
- Loading/error state documentation depth
- All technical implementation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOC-01 | README has project overview in Norwegian with display photo placeholder | Codebase analysis: project description from pyproject.toml, display zones from layout.py, image placeholder HTML pattern |
| DOC-02 | README has 64x64 zone layout diagram (ASCII art) | Exact zone definitions from layout.py: clock(0-10), date(11-18), divider(19), bus(20-38), divider(39), weather(40-63) |
| DOC-03 | README has prerequisites section (Python 3.10+, Pixoo 64, LAN) | pyproject.toml requires-python >=3.10; dependencies: pixoo, Pillow>=12.1.0, discord.py>=2.0, python-dotenv>=1.0 |
| DOC-04 | README has installation guide (clone, venv, pip install) | Standard Python project setup; pyproject.toml uses modern pip install pattern |
| DOC-05 | README has configuration guide (.env variables with required/optional flags) | Full .env.example analysis: DIVOOM_IP, BUS_QUAY_DIR1/DIR2, WEATHER_LAT/LON (required); ET_CLIENT_NAME, WEATHER_USER_AGENT, DISCORD_BOT_TOKEN/CHANNEL_ID, BIRTHDAY_DATES (optional) |
| DOC-06 | README has usage section (running, --simulated, --save-frame) | main.py argparse: --ip, --simulated, --save-frame; TEST_WEATHER env var for visual testing |
| DOC-07 | README has launchd service setup (step-by-step) | com.divoom-hub.dashboard.plist exists with inline installation comments |
| DOC-08 | README has "Bygget med Claude Code" badge and AI transparency section | shields.io badge URL pattern researched; link target and section depth at Claude's discretion |
| DOC-09 | README has architecture overview (module map, data flow) | Full module tree analyzed: src/{config, main, device/, display/, providers/} with clear separation of concerns |
| DOC-10 | README has API documentation (Entur, MET Norway gotchas) | Entur JourneyPlanner v3 GraphQL API with ET-Client-Name header; MET Locationforecast 2.0 with If-Modified-Since caching and User-Agent requirement |
| DOC-11 | README has Discord message override section | discord_bot.py: MessageBridge pattern, daemon thread, channel-specific listening, clear/cls/reset commands |
| DOC-12 | README has weather animation documentation (3D depth system) | weather_anim.py: 8 animation types (rain, snow, cloud, sun, thunder, fog, clear, sleet), bg/fg layer compositing for depth effect, ~3 FPS at 0.35s tick |
| DOC-13 | README documents Norwegian character support (BDF fonts, aeoeaa) | fonts.py: BDF-to-PIL conversion; clock.py: Norwegian day/month names with oe; 3 BDF fonts (4x6, 5x8, 7x13) |
| DOC-14 | README documents error resilience (staleness dot, fallback, 300-push refresh) | main.py: staleness tracking (bus 3m/10m, weather 30m/1h), orange dot indicator, last-good-data preservation, pixoo_client.py: auto connection refresh, 90% brightness cap |
| DOC-15 | README mentions birthday easter egg | config.py: BIRTHDAY_DATES env var (MM-DD format); renderer.py: golden clock, pink date, crown icon, sparkle pixels |
</phase_requirements>

## Standard Stack

This is a documentation-only phase. No new libraries or code changes.

### Core Tools
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| Markdown | README format | GitHub native rendering, universal standard |
| shields.io | Badge generation | De facto standard for GitHub README badges |
| ASCII art | Display layout diagrams | Works in all terminals and GitHub rendering |

### Badge Pattern
The "Bygget med Claude Code" badge should use shields.io static badge format:
```markdown
[![Bygget med Claude Code](https://img.shields.io/badge/Bygget_med-Claude_Code-orange?style=flat&logo=claude&logoColor=white)](https://claude.ai/code)
```

Note: The `claude` logo may not be on shields.io/simpleicons. Alternatives:
- Use `anthropic` as logo name
- Use a generic AI icon
- Use no logo (text-only badge is still effective)

## Architecture Patterns

### Codebase Structure (for DOC-09)
```
divoom-hub/
├── src/
│   ├── main.py           # Entry point, main loop, CLI args
│   ├── config.py          # All configuration (.env loading, constants)
│   ├── device/
│   │   └── pixoo_client.py  # Pixoo 64 communication wrapper
│   ├── display/
│   │   ├── fonts.py       # BDF font loading/conversion
│   │   ├── layout.py      # Zone definitions, colors, pixel coordinates
│   │   ├── renderer.py    # PIL compositor (state -> 64x64 image)
│   │   ├── state.py       # DisplayState dataclass (dirty flag pattern)
│   │   ├── weather_anim.py  # 8 animation types with bg/fg depth layers
│   │   └── weather_icons.py # Pixel art weather icons (10x10)
│   └── providers/
│       ├── bus.py         # Entur JourneyPlanner v3 GraphQL
│       ├── clock.py       # Norwegian time/date formatting
│       ├── discord_bot.py # Discord message override (daemon thread)
│       └── weather.py     # MET Norway Locationforecast 2.0
├── assets/fonts/          # BDF bitmap fonts (4x6, 5x8, 7x13)
├── tests/                 # pytest test suite
├── .env.example           # Configuration template
├── pyproject.toml         # Project metadata and dependencies
└── com.divoom-hub.dashboard.plist  # macOS launchd service
```

### Data Flow (for DOC-09)
```
main_loop() ──┬── fetch_bus_data() ──> Entur GraphQL API (every 60s)
              ├── fetch_weather_safe() ──> MET Norway API (every 600s)
              ├── weather_anim.tick() ──> bg/fg RGBA layers (~3 FPS)
              ├── DisplayState.from_now() ──> dirty flag check
              ├── render_frame() ──> 64x64 PIL Image
              └── client.push_frame() ──> Pixoo 64 HTTP API
```

### Display Zone Layout (for DOC-02)
```
┌────────────────────────────────────────────────────────────────┐
│ 14:32  ☀                                                CLOCK │ y=0-10   (11px)
│ tor 20. feb                                              DATE │ y=11-18  (8px)
├────────────────────────────────────────────────────────────────┤ y=19     (1px divider)
│ <S  5  12  25                                             BUS │ y=20-29  (dir1: 9px)
│ >L  3  8   18                                             BUS │ y=30-38  (dir2: 9px)
├────────────────────────────────────────────────────────────────┤ y=39     (1px divider)
│ 7°  2.3mm         ☁                                  WEATHER │ y=40-63  (24px)
│ 5/2                ☁☁                                         │
│           ☁☁☁☁☁                                               │
└────────────────────────────────────────────────────────────────┘
```

### Zone Reference Table (for DOC-02)
| Zone | Y Start | Y End | Height | Content |
|------|---------|-------|--------|---------|
| Clock | 0 | 10 | 11px | HH:MM + weather icon + birthday crown |
| Date | 11 | 18 | 8px | Norwegian "tor 20. feb" |
| Divider 1 | 19 | 19 | 1px | Teal separator line |
| Bus | 20 | 38 | 19px | Two direction lines with urgency colors |
| Divider 2 | 39 | 39 | 1px | Teal separator line |
| Weather | 40 | 63 | 24px | Temp, high/low, rain, animated overlay |

## Don't Hand-Roll

Not applicable -- documentation-only phase. No code to build.

## Common Pitfalls

### Pitfall 1: Leaking Personal Data
**What goes wrong:** Real GPS coordinates, real bus stop IDs, real Discord tokens appear in README examples.
**Why it happens:** Copy-pasting from actual .env or real config during documentation writing.
**How to avoid:** Use clearly fake placeholder values. .env.example already has safe defaults (59.9139/10.7522 = Oslo city center, generic quay IDs). Follow this pattern.
**Warning signs:** Values that look like real NSR:Quay IDs, real bot tokens, or specific home coordinates.

### Pitfall 2: Stale Documentation
**What goes wrong:** README describes features or config that don't match the actual codebase.
**Why it happens:** Writing documentation from memory rather than reading actual source code.
**How to avoid:** Every technical claim in the README should be verifiable against the actual source files. The research above catalogues the real values.
**Warning signs:** Wrong file paths, wrong environment variable names, wrong default values.

### Pitfall 3: Image Placeholder Breaking
**What goes wrong:** The display photo placeholder shows a broken image icon or renders badly.
**Why it happens:** Using `<img>` tags without proper alt text or fallback, or linking to non-existent files.
**How to avoid:** Use HTML `<img>` tag with descriptive alt text and optional `onerror` fallback, or use markdown image syntax with good alt text: `![Pixoo 64-dashbordet i aksjon](docs/display-photo.jpg)`. Missing images in GitHub render as the alt text cleanly.
**Warning signs:** Broken image icons in rendered README.

### Pitfall 4: Norwegian Language Inconsistency
**What goes wrong:** Mixing nynorsk and bokmaal forms, or switching between formal and informal tone.
**Why it happens:** AI models sometimes mix Norwegian dialects.
**How to avoid:** Stick strictly to bokmaal. Use informal/personal tone throughout (du-form, not De-form). Technical English terms are acceptable when they're standard in Norwegian tech contexts (e.g., "repository", "API", "daemon").
**Warning signs:** "Me" instead of "vi", "korleis" instead of "hvordan", "bruke" vs "nytte".

### Pitfall 5: Overly Long README
**What goes wrong:** README becomes a wall of text that nobody reads.
**Why it happens:** 15 requirements = potentially massive document.
**How to avoid:** Use collapsible `<details>` sections for deep-dive content. Keep the "above the fold" content scannable (overview, badge, quick-start). Technical deep dives can be collapsed.
**Warning signs:** README exceeds ~500 lines without any collapsible sections.

## Code Examples

Not applicable -- documentation-only phase. However, the README will contain code blocks for:

### Installation Commands
```bash
git clone https://github.com/YOUR_USERNAME/divoom-hub.git
cd divoom-hub
python -m venv .venv
source .venv/bin/activate
pip install .
```

### Running the Dashboard
```bash
# Normal mode (hardware required)
python src/main.py

# Simulator mode (no hardware needed)
python src/main.py --simulated

# Debug mode (saves each frame)
python src/main.py --save-frame

# Test weather animation
TEST_WEATHER=rain python src/main.py --simulated
```

### .env Configuration Template
```bash
# === PÅKREVD ===
DIVOOM_IP=192.168.1.100
BUS_QUAY_DIR1=NSR:Quay:XXXXX
BUS_QUAY_DIR2=NSR:Quay:XXXXX
WEATHER_LAT=59.9139
WEATHER_LON=10.7522

# === VALGFRITT ===
# ET_CLIENT_NAME=mitt-pixoo-dashbord
# WEATHER_USER_AGENT=pixoo-dashboard/1.0 epost@eksempel.no
# DISCORD_BOT_TOKEN=din-bot-token-her
# DISCORD_CHANNEL_ID=123456789012345678
# BIRTHDAY_DATES=01-01,06-15
```

### launchd Installation
```bash
# 1. Rediger stier i plist-filen
# 2. Kopier til LaunchAgents
cp com.divoom-hub.dashboard.plist ~/Library/LaunchAgents/

# 3. Last inn tjenesten
launchctl load ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist

# 4. Sjekk status
launchctl list | grep divoom

# 5. Stopp tjenesten
launchctl unload ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist

# 6. Se logger
tail -f /tmp/divoom-hub.log
```

## State of the Art

| Area | Current Approach in Codebase | Notes |
|------|------------------------------|-------|
| Weather API | MET Locationforecast 2.0 (compact endpoint) | Current stable API; uses If-Modified-Since caching per TOS |
| Bus API | Entur JourneyPlanner v3 (GraphQL) | Current stable API; requires ET-Client-Name header |
| Display lib | pixoo (Python) with refresh_connection_automatically | Handles the ~300-push lockup automatically |
| Fonts | BDF bitmap fonts via Pillow BdfFontFile | Classic approach for pixel displays; 3 sizes available |
| Animation | PIL RGBA compositing with bg/fg depth layers | Custom but appropriate for 64x64 pixel art animation |

## Open Questions

1. **Badge logo availability**
   - What we know: shields.io uses simpleicons.org for logos
   - What's unclear: Whether "claude" or "anthropic" exists as a simpleicons icon
   - Recommendation: Test badge URL; fall back to text-only badge if logo unavailable

2. **README length management**
   - What we know: 15 requirements will produce a substantial document
   - What's unclear: Exact balance of collapsed vs expanded sections
   - Recommendation: Keep quick-start above the fold; collapse architecture, API details, and animation docs

## Sources

### Primary (HIGH confidence)
- Direct source code analysis of all files in `src/` directory (2,350 LOC)
- `pyproject.toml` for project metadata and dependencies
- `.env.example` for configuration documentation
- `com.divoom-hub.dashboard.plist` for launchd setup
- `src/display/layout.py` for exact zone pixel coordinates and color values

### Secondary (MEDIUM confidence)
- shields.io badge documentation (https://shields.io/badges)
- GitHub README rendering documentation (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
- General README best practices (https://www.makeareadme.com/)

## Metadata

**Confidence breakdown:**
- Codebase documentation accuracy: HIGH - direct source code analysis, every value verified
- README structure: HIGH - well-established patterns for GitHub projects
- Norwegian language: MEDIUM - bokmaal is well-defined but AI generation needs review
- Badge implementation: MEDIUM - shields.io API is stable but logo availability unverified

**Research date:** 2026-02-21
**Valid until:** 2026-04-21 (documentation patterns are stable; codebase may change with new features)
