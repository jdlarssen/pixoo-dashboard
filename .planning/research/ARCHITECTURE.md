# Architecture Patterns

**Domain:** v1.1 integration -- Norwegian README + weather color fix on existing Pixoo 64 dashboard
**Researched:** 2026-02-21
**Confidence:** HIGH (existing codebase fully audited, both changes are well-scoped)

## Current Architecture (As-Built v1.0)

```
divoom-hub/
├── src/
│   ├── main.py                    # Entry point, main loop, data refresh scheduling
│   ├── config.py                  # .env-based config (DEVICE_IP, API keys, intervals)
│   ├── device/
│   │   └── pixoo_client.py        # Pixoo 64 connection, rate-limited push, brightness
│   ├── display/
│   │   ├── state.py               # DisplayState dataclass (equality for dirty flag)
│   │   ├── layout.py              # Zone definitions + ALL color constants
│   │   ├── renderer.py            # PIL compositor: state + fonts + anim -> 64x64 RGB
│   │   ├── weather_anim.py        # 8 animation classes, bg/fg depth layers (RGBA)
│   │   ├── weather_icons.py       # 10px programmatic pixel art icons, symbol mapping
│   │   └── fonts.py               # BDF-to-PIL font loader
│   └── providers/
│       ├── clock.py               # Norwegian time/date formatting
│       ├── bus.py                  # Entur GraphQL bus departures
│       ├── weather.py             # MET Norway Locationforecast 2.0
│       └── discord_bot.py         # MessageBridge + bot thread for display override
├── assets/fonts/                  # BDF bitmap fonts (4x6, 5x8)
├── tests/                         # 96 tests (clock, bus, weather, renderer, anim, fonts)
├── .env.example                   # Configuration template
├── .env                           # User's actual config (gitignored)
├── pyproject.toml                 # Project metadata, dependencies
├── com.divoom-hub.dashboard.plist # macOS launchd service wrapper
└── debug_frame.png                # Last rendered frame (for development)
```

**No README.md exists.** The project root has zero documentation files.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `config.py` | Load .env, validate, expose constants | All modules import from it |
| `layout.py` | Zone pixel coords, ALL color constants | `renderer.py` imports zones + colors |
| `weather_anim.py` | 8 animation types, produces (bg, fg) RGBA layers | `renderer.py` composites them, `main.py` selects animation |
| `renderer.py` | Composites DisplayState + fonts + anim into 64x64 RGB | Reads from `layout.py`, `state.py`, `weather_icons.py` |
| `state.py` | DisplayState dataclass with `from_now()` factory | `main.py` creates, `renderer.py` reads |
| `main.py` | Main loop, scheduling, data refresh coordination | Orchestrates everything |
| `pixoo_client.py` | Device push, rate limiting, brightness | Called by `main.py` |
| `providers/*.py` | Fetch data from external APIs | Called by `main.py`, results flow into DisplayState |

## v1.1 Changes: What Integrates Where

### Change 1: Norwegian README (README.md at project root)

**Type:** NEW FILE -- zero integration with existing code.

**File:** `/README.md` (project root)

**Integration points:** None. The README is a documentation file. It describes the existing architecture but does not touch any source code.

**Content sources (data to document, not code changes):**
- Project overview: from `PROJECT.md` context
- Setup instructions: from `.env.example` (config template)
- Architecture diagram: from existing `src/` structure
- Zone layout: from `layout.py` (CLOCK_ZONE, DATE_ZONE, etc.)
- API documentation: from `bus.py` (Entur) and `weather.py` (MET Norway)
- Service setup: from `com.divoom-hub.dashboard.plist`
- Discord integration: from `discord_bot.py`
- Claude Code badge: static markdown badge element

**Dependencies on existing code:** Read-only. README reads from the codebase to describe it; no code imports the README.

**Test impact:** None. README does not change any behavior.

### Change 2: Weather Animation/Rain Text Color Fix

**Type:** MODIFY EXISTING FILES -- targeted color constant changes.

**Problem (from todo):** Rain/snow animation particles and rain indicator text ("1/1mm") are both grey/blue, making them indistinguishable on the physical LED display. User reported: "The raindrops, or is it snow? I don't know, they are grey. So are the letters for 1/1."

**Root cause:** The rain particles use `(40, 90, 200)` for far drops and `(60, 140, 255)` for near drops. Snow particles use `(200, 210, 230)` for far and `(255, 255, 255)` for near. The rain indicator text uses `COLOR_WEATHER_RAIN = (50, 180, 255)` -- vivid blue. On the LED, the rain particles and the rain text are both blue-ish tones that blend together. Snow particles in grey-white are also difficult to distinguish from rain.

#### Files to Modify

| File | What Changes | Why |
|------|-------------|-----|
| `src/display/weather_anim.py` | Rain particle fill colors in `RainAnimation.tick()` | Make rain particles distinctly blue (brighter, more saturated) vs current muted blue |
| `src/display/weather_anim.py` | Snow particle fill colors in `SnowAnimation.tick()` | Make snow clearly white/bright, not grey-ish (current `(200, 210, 230)` is grey) |
| `src/display/layout.py` | `COLOR_WEATHER_RAIN` constant | Change rain text color to a distinct hue from rain particle blue (e.g., cyan, or keep blue but change particle colors) |

#### Specific Code Locations

**`weather_anim.py` -- RainAnimation.tick() (lines 76-95):**
```python
# Current far drop color:
bg_draw.line([...], fill=(40, 90, 200, 100))     # muted blue, alpha 100
# Current near drop color:
fg_draw.line([...], fill=(60, 140, 255, 200))     # medium blue, alpha 200
```
These need to shift to ensure rain reads as distinct blue water droplets, not grey.

**`weather_anim.py` -- SnowAnimation.tick() (lines 154-176):**
```python
# Current far flake color:
bg_draw.point((x, y), fill=(200, 210, 230, 90))   # grey-blue, alpha 90
# Current near flake crystal color (via _draw_crystal):
color = (255, 255, 255, 180)                        # white, alpha 180
```
Far flakes are grey (`200, 210, 230`) which looks similar to rain. They should be brighter white.

**`layout.py` -- COLOR_WEATHER_RAIN (line 61):**
```python
COLOR_WEATHER_RAIN = (50, 180, 255)   # Vivid blue for rain indicator text
```
This is visually close to rain particle blue. Change to a distinct hue that contrasts with both rain and snow particle colors.

#### Integration Constraints

1. **Color palette coherence:** Weather zone already uses these colors:
   - `COLOR_WEATHER_TEMP = (255, 200, 50)` -- warm yellow for temperature
   - `COLOR_WEATHER_TEMP_NEG = (80, 200, 255)` -- cyan-blue for negative temp
   - `COLOR_WEATHER_HILO = (120, 180, 160)` -- soft teal for high/low
   - `COLOR_WEATHER_RAIN = (50, 180, 255)` -- vivid blue for rain text
   New colors must not clash with these existing constants.

2. **Alpha compositing pipeline:** Colors are composited via `_composite_layer()` in `renderer.py` (lines 121-125). This function does `Image.alpha_composite(zone_region, layer)` -- a single alpha application (the double-alpha bug was fixed in v1.0 plan 03-03). New alpha values must work through this single-pass composite.

3. **3D depth contract:** `weather_anim.py` produces `(bg_layer, fg_layer)` tuples. Background layer renders behind text (dimmer), foreground renders in front (brighter). This depth layering must be preserved -- far particles stay dimmer than near particles.

4. **Other animations affected:** Changing the color strategy for rain/snow may suggest reviewing all 8 animation types for visual consistency, but only rain and snow are explicitly broken. Cloud, sun, thunder, fog are distinguishable. Thunder reuses `RainAnimation` internally, so rain color changes propagate to thunder automatically.

5. **Test impact:** `tests/test_weather_anim.py` tests animation frame generation. Color changes should not break structural tests (they verify frame shapes and particle counts, not specific color values). No test changes expected.

#### Color Fix Strategy

The core problem is **rain particles vs rain text** both being blue, and **rain particles vs snow particles** both being grey-ish.

**Recommended approach -- differentiate by weather type color identity:**

| Element | Current Color | Recommended Color | Rationale |
|---------|--------------|-------------------|-----------|
| Rain far drops | `(40, 90, 200, 100)` grey-blue | `(70, 130, 255, 100)` brighter blue | Make rain clearly blue, not grey |
| Rain near drops | `(60, 140, 255, 200)` medium blue | `(80, 160, 255, 200)` vivid blue | Slightly brighter near drops for depth |
| Snow far flakes | `(200, 210, 230, 90)` grey | `(220, 230, 255, 90)` cool white | White, not grey -- clearly snow |
| Snow near crystal | `(255, 255, 255, 180)` white | Keep as-is | Already bright white |
| Rain text ("1/1mm") | `(50, 180, 255)` vivid blue | `(100, 220, 255)` light cyan | Distinct from rain particle blue, still reads as "water" |

The key insight: rain particles should be vivid blue, snow particles should be bright white, and rain text should be light cyan to differentiate from particle blue. This creates three distinct visual channels.

## Data Flow for Color Fix

```
Weather condition changes (main.py)
  │
  v
get_animation(weather_group)          # weather_anim.py -- selects animation class
  │
  v
animation.tick()                       # produces (bg_layer, fg_layer) RGBA
  │                                    # << COLOR CHANGES HERE in fill= parameters >>
  v
render_weather_zone(...)              # renderer.py
  ├── _composite_layer(bg_layer)      # behind text
  ├── draw.text(rain_text, COLOR_WEATHER_RAIN)  # << COLOR CHANGE HERE >>
  └── _composite_layer(fg_layer)      # in front of text
  │
  v
render_frame() -> 64x64 RGB Image
  │
  v
pixoo_client.push_frame()
```

The color changes are purely in the rendering data (fill colors and color constants). No flow changes, no structural changes, no API changes.

## Patterns to Follow

### Pattern 1: Color Constants in layout.py

**What:** All user-visible colors are defined as named constants in `layout.py`, imported by `renderer.py`.

**When:** For text colors and UI element colors that form the design palette.

**Current practice:** `renderer.py` imports `COLOR_WEATHER_RAIN` from `layout.py`. Any rain text color change goes in `layout.py`.

**Note:** Animation particle colors are currently hardcoded inline in `weather_anim.py` as `fill=(R, G, B, A)` tuples in each `tick()` method. These are NOT in `layout.py`. This is an existing pattern -- the animation colors were always inline because they include alpha values and are animation-specific, not part of the static UI palette. Keep this pattern for v1.1; refactoring to layout.py constants is optional polish.

### Pattern 2: New Documentation at Root

**What:** README.md is a single file at the project root. No docs/ directory, no multi-file documentation structure.

**When:** This project is small enough (17 source files, 2,321 LOC) that a single comprehensive README covers everything.

**Rationale:** Adding a docs/ folder for a project this size is over-engineering. The README should be self-contained with all sections: overview, setup, architecture, API docs, service config, development.

### Pattern 3: Test Mode for Visual Verification

**What:** `main.py` supports `TEST_WEATHER=rain python src/main.py --simulated --save-frame` to visually verify animation rendering.

**When:** After color changes, use this to verify the new colors look correct on the simulated display or in `debug_frame.png`.

**Why relevant:** The color fix cannot be fully verified in unit tests -- it requires visual inspection on actual LED hardware or at minimum the simulator. The test mode is the existing tool for this.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Extracting Animation Colors to Config

**What:** Moving animation particle colors to `config.py` or `.env` as configurable values.
**Why bad:** These are visual design decisions tuned for specific LED hardware, not user preferences. Making them configurable would create a false sense of flexibility while making the visual design harder to maintain as a coherent whole. The 3D depth system requires careful balance between bg/fg alpha values.
**Instead:** Keep animation colors as hardcoded fill values in `weather_anim.py`. Keep the palette consistent by reviewing all animation types together during the color fix.

### Anti-Pattern 2: Adding an English README Alongside Norwegian

**What:** Creating both README.md (English) and README.no.md (Norwegian).
**Why bad:** The project requirement is specifically a Norwegian README. The user preference is Norwegian language for this personal dashboard project. Maintaining two README files doubles documentation maintenance.
**Instead:** Single README.md in Norwegian. Code comments and docstrings remain in English (they already are and should stay that way).

### Anti-Pattern 3: Changing Compositing Logic During Color Fix

**What:** Modifying `_composite_layer()` in `renderer.py` while fixing colors.
**Why bad:** The compositing was fixed in v1.0 phase 03-03 after a thorough debug session. It works correctly now (single alpha application). Changing it alongside color values makes it impossible to isolate which change affected the visual result.
**Instead:** Only change fill color values and color constants. If compositing issues resurface, that is a separate investigation.

## Build Order Recommendation

**Color fix first, then README.**

### Rationale:

1. **Color fix informs README content.** The README should document the current state of the project, including weather animations. If colors are wrong when the README is written, the README would describe a broken state. Fix first, document the fixed state.

2. **Color fix has test dependencies.** The fix needs visual verification (`TEST_WEATHER` mode, `--save-frame`, ideally hardware test). This is faster to iterate on without the context switch of writing documentation.

3. **README has zero code dependencies.** The README can be written at any point since it does not modify any source files. It reads FROM the codebase but does not write TO it.

4. **Independent work streams.** These two changes touch completely different files with zero overlap:
   - Color fix: `src/display/weather_anim.py`, `src/display/layout.py`
   - README: `README.md` (new file at root)

### Suggested Phase Structure:

```
Phase 1: Weather Color Fix
  Files modified: weather_anim.py, layout.py
  Verification: TEST_WEATHER=rain/snow --save-frame, visual inspection
  Risk: Low (color values only, no structural changes)

Phase 2: Norwegian README
  Files created: README.md
  Content sources: PROJECT.md, .env.example, layout.py, all src/ modules
  Verification: Read-through, ensure all sections match actual codebase
  Risk: None (documentation only)
```

## File Change Summary

| File | Action | Change Type | Lines Affected |
|------|--------|-------------|---------------|
| `README.md` | CREATE | New documentation file | N/A (new) |
| `src/display/weather_anim.py` | MODIFY | Fill color tuples in RainAnimation.tick(), SnowAnimation.tick() | ~4 lines (2 rain colors, 2 snow colors) |
| `src/display/layout.py` | MODIFY | `COLOR_WEATHER_RAIN` constant value | 1 line |

**Total code changes: ~5 lines across 2 files.**
**Total new files: 1 (README.md).**

No test changes expected. No config changes. No dependency changes. No architectural changes.

## Sources

- Codebase audit: all 17 source files read and analyzed (HIGH confidence)
- Debug session: `.planning/debug/weather-animation-too-subtle.md` -- compositing fix history (HIGH confidence)
- Todo: `.planning/todos/done/2026-02-20-weather-animation-and-rain-text-colors-indistinguishable.md` -- problem statement (HIGH confidence)
- Project context: `.planning/PROJECT.md` -- requirements and constraints (HIGH confidence)

---
*Architecture research for: Divoom Hub v1.1 Documentation & Polish*
*Researched: 2026-02-21*
