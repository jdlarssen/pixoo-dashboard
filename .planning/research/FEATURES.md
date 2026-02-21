# Feature Landscape

**Domain:** Norwegian README documentation + LED weather color fix for Pixoo 64 dashboard
**Researched:** 2026-02-21
**Milestone:** v1.1 Documentation & Polish

## Table Stakes

Features users expect. Missing = project feels incomplete.

### README Documentation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Prosjektbeskrivelse (overview) | First thing visitors read; explains what the display does and why | Low | 2-3 paragraphs covering: what it is (always-on entryway dashboard), what it shows (klokke, buss, vaer), and the core value (glance without pulling out your phone). A photo of the running display elevates this from good to great |
| Installasjon (installation) | Users need to go from zero to running | Low | Clone, `python -m venv .venv`, `pip install .`, copy `.env.example` to `.env`. The existing `.env.example` has excellent inline docs already -- reference it rather than duplicating |
| Oppsett / Konfigurasjon (configuration) | 7+ env vars that need explaining, some with non-obvious values | Low | Table of all `.env` variables with required/optional flags. Key guidance: how to find your bus stop quay IDs from stoppested.entur.org, how to find coordinates for weather, MET User-Agent requirements |
| Bruk (usage) | How to start the dashboard | Low | `python src/main.py --ip X.X.X.X`, `--simulated` for testing without hardware, `--save-frame` for debugging. Document `TEST_WEATHER` env var for visual testing of weather animations |
| Kjore som tjeneste (launchd service) | The plist exists but needs user-facing docs | Low | Step-by-step: edit paths in plist, `cp` to `~/Library/LaunchAgents/`, `launchctl load`, check status, view logs. Already documented in plist XML comments -- extract and format for README |
| Skjermoppsett (display layout) | The 64x64 pixel budget is the project's core constraint | Low | ASCII art zone diagram: klokke 11px, dato 8px, skillelinje 1px, buss 19px, skillelinje 1px, vaer 24px = 64px. This makes the project tangible to readers |
| Krav (requirements) | What you need before starting | Low | Python 3.10+, Pixoo 64 on same LAN, macOS for launchd (note: systemd alternative for Linux). List pip dependencies from pyproject.toml |

### Weather Color Fix

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Rain text vs rain animation distinguishability | Reported as indistinguishable on physical hardware. `COLOR_WEATHER_RAIN (50, 180, 255)` clashes with rain drops `(40, 90, 200)` far and `(60, 140, 255)` near | Low | All three are blue-family hues. On LED at 2+ meters, perceptual distance is too small. This is the primary bug |
| Verify all text-animation combinations | After fixing rain, confirm the other 7 animation types don't have similar issues | Low | Systematic check: temperature text vs each animation, hi/lo text vs each animation, rain indicator text vs each animation. Most are already fine based on code analysis |

## Differentiators

Features that set the project apart. Not expected, but valued.

### README Documentation

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Bygget med Claude Code" transparency section | Honest about AI-assisted development process. Explicitly requested in milestone | Low | Shield.io badge at top of README + short section explaining the development process. Link to Anthropic/Claude Code. This is not just a badge -- it tells the story of how the project was built |
| Vaeranimasjoner (weather animation docs) | The 3D depth-layered animation system is the most impressive technical feature | Med | Describe bg/fg compositing, the 6 animation types (rain, snow, sun, fog, clouds, thunder), alpha tuning (65-180 range) for LED hardware. A screenshot or GIF would add significant value but is optional |
| Arkitektur / Oversikt (architecture) | Clean module structure deserves documentation | Med | Module map: `src/display/` (renderer, layout, state, fonts, weather_anim, weather_icons), `src/providers/` (clock, bus, weather, discord_bot), `src/device/` (pixoo_client). Data flow: providers fetch -> DisplayState -> renderer composites -> pixoo_client pushes |
| API-dokumentasjon (external APIs) | Two APIs with specific requirements that tripped up development | Med | Entur JourneyPlanner v3 GraphQL (quay IDs, ET-Client-Name header, refresh rate), MET Locationforecast 2.0 (User-Agent required, If-Modified-Since caching, rate limits). Document the gotchas |
| Discord-meldinger (Discord integration) | Not obvious that a pixel display can receive push messages | Low | Brief section: create Discord bot, get token, set channel ID in .env, send `!msg hello` in the channel. Explain MessageBridge thread safety |
| Bursdagspaaskeegg (birthday easter egg) | Fun personal touch | Low | Mention `BIRTHDAY_DATES` env var, describe golden crown + sparkles effect on configured dates |
| Feilhaandtering (error resilience docs) | Engineering choices worth documenting for other builders | Low | Staleness indicators (orange dot), fallback to last-good data, 300-push connection refresh, graceful degradation |
| Norsk tegnsett (Norwegian character support) | Solved a non-trivial problem: aeoaa on pixel displays | Low | Explain why custom rendering was needed (native Pixoo has no aeoaa), which BDF fonts (hzeller 4x6, 5x8), how they were validated |

### Weather Color Fix

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Perceptually distinct color palette | Each weather state has a clear visual identity that never clashes with overlaid text | Med | Not just fixing one color -- opportunity to verify the entire palette is LED-safe. But scope should be limited to actual problems |
| Maintain rain's blue identity in animation | Rain animation should still feel blue/watery | Low | Fix the TEXT color, not the animation. The rain drops are the artistic element; the "2.5mm" text is informational |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| English README alongside Norwegian | Milestone explicitly calls for Norwegian README. Dual-language doubles maintenance for a personal project | Single Norwegian README in Bokmal. English speakers can use browser translation. One-line English summary at the very top is fine |
| Nynorsk variant | The user writes Bokmal. Nynorsk is a separate written standard used by ~10% of Norwegians. Adding it doubles maintenance with no benefit for this personal project | Write consistently in Bokmal |
| Auto-generated API reference (Sphinx/mkdocs) | 2,321 LOC codebase with good existing docstrings. Auto-doc tooling adds build complexity disproportionate to project size | Good docstrings in code (already present) + architecture section in README |
| Interactive color picker / configurable colors | Over-engineering. The color problem needs 1-2 constant changes in layout.py, not a configuration system | Hardcode correct LED-safe colors. Document the color palette in README for anyone forking |
| Per-weather-condition text color overrides | Adds complexity (8 weather conditions x N text elements) for minimal gain | Use text colors that contrast with ALL animation types, not per-type overrides |
| Comprehensive Norwegian translation of code comments | Code comments and docstrings are in English by convention. Translating them adds no value and makes the code harder to maintain | Keep code in English, README in Norwegian |

## Feature Dependencies

```
README (all sections can be written in parallel, but logical reading order matters):
  Prosjektbeskrivelse -> Krav -> Installasjon -> Oppsett -> Bruk -> Tjeneste
  Skjermoppsett (standalone, can be placed after Bruk)
  Arkitektur (standalone, references module structure)
  API-dokumentasjon (standalone, references Oppsett for env vars)
  Discord-meldinger (requires Oppsett context)
  Vaeranimasjoner (requires Arkitektur context)
  Bursdagspaaskeegg (standalone mini-section)
  Feilhaandtering (requires Arkitektur context)
  "Bygget med Claude Code" (standalone, placed at end or as badge at top)

Weather Color Fix:
  Identify clashing colors in layout.py -> Choose replacement -> Update constant
  -> Verify all 8 weather animation types still work -> Hardware test
  (No dependency on README features -- can be done in parallel)
```

## MVP Recommendation

### README: Write in this order

1. **Prosjektbeskrivelse** -- the hook. What it is, what it shows, why it exists. Include display photo if available
2. **Skjermoppsett** -- the 64x64 zone layout diagram. Makes the project tangible immediately
3. **Krav + Installasjon + Oppsett + Bruk** -- practical core. Clone to running in 5 minutes
4. **Kjore som tjeneste** -- launchd for always-on operation
5. **"Bygget med Claude Code"** -- transparency badge and section (explicitly requested in milestone)
6. **Arkitektur** -- module map and data flow for anyone forking or understanding the code
7. **Remaining differentiators** -- API docs, Discord, birthday, error handling, animations, Norwegian chars

**Defer:** None. This is a documentation milestone -- all sections should be written. The ordering above is priority for the reader experience, not a phasing suggestion.

### Weather Color Fix: Specific recommendation

**The problem:** `COLOR_WEATHER_RAIN = (50, 180, 255)` (vivid blue) is rendered as rain indicator text ("2.5mm") in the weather zone. This text sits inside the rain animation, where drops are `(40, 90, 200, alpha=100)` (far/dim) and `(60, 140, 255, alpha=200)` (near/bright). All three are blue-family hues. On a 64x64 LED matrix viewed at 2+ meters, the perceptual distance between these colors is below the just-noticeable-difference threshold, making the text invisible during rain.

**Analysis of current color usage in weather zone:**

| Element | Current Color | RGB | Against Rain Anim | Status |
|---------|--------------|-----|-------------------|--------|
| Temperature (positive) | `COLOR_WEATHER_TEMP` | `(255, 200, 50)` | Warm yellow vs blue drops | OK -- high contrast |
| Temperature (negative) | `COLOR_WEATHER_TEMP_NEG` | `(80, 200, 255)` | Cyan vs blue drops | Borderline -- cyan is close to blue but distinct enough due to green channel. Monitor but no fix needed now |
| High/Low text | `COLOR_WEATHER_HILO` | `(120, 180, 160)` | Teal vs blue drops | OK -- green channel separates it |
| Rain indicator | `COLOR_WEATHER_RAIN` | `(50, 180, 255)` | Blue vs blue drops | BROKEN -- same hue family, alpha blending makes it worse |
| Snow crystals (anim) | N/A | `(255, 255, 255, 180)` | White vs any text | OK -- snow is bright white, text colors are all distinct |
| Sun rays (anim) | N/A | `(255, 230, 90)` | Yellow vs temp text | Borderline -- same yellow family, but sun animation alpha is low enough that text reads through |

**The fix:** Change `COLOR_WEATHER_RAIN` to a color that contrasts with blue rain drops. Recommended:

| Option | RGB Value | Rationale | LED Readability |
|--------|-----------|-----------|-----------------|
| **Bright white** | `(255, 255, 255)` | Maximum luminance contrast against blue. Industry standard for info text on dark LED backgrounds. White reads through every animation type | BEST |
| **Warm yellow** | `(255, 220, 100)` | Close to `COLOR_MESSAGE` yellow family. Yellow-on-blue is the #1 LED sign readability combination per signage research. Semantic risk: could confuse with temperature display | GOOD |
| **Light cyan-white** | `(200, 240, 255)` | Stays in cool-water family while adding enough brightness to separate from pure blue drops. Subtlest change | ADEQUATE |

**Recommendation:** Use `(255, 255, 255)` bright white because:
1. Rain indicator text ("2.5mm") is purely informational -- it conveys a number, not a mood. Readability is paramount
2. White has maximum luminance contrast against every animation type: blue rain, grey clouds, yellow sun, white snow (snow animation occupies different zone space), grey fog
3. LED sign research consistently ranks white-on-dark as the most readable combination, with a brightness differential well above the 70% threshold for assured legibility
4. The 4x6 "tiny" font used for rain text is already at the minimum readable size -- it cannot afford ANY contrast reduction
5. Simple one-line change in `layout.py`: `COLOR_WEATHER_RAIN = (255, 255, 255)`

**What NOT to change:** No changes needed for `COLOR_WEATHER_TEMP`, `COLOR_WEATHER_TEMP_NEG`, `COLOR_WEATHER_HILO`, or any animation colors. The bug is specifically the rain indicator text vs rain animation overlap.

## Sources

- [LED Sign Color Combos for Visibility](https://www.ledsignsupply.com/designing-eye-catching-content-for-outdoor-led-signs/) -- Yellow/white on dark as top LED readability combinations (MEDIUM confidence)
- [Signage and Color Contrast](https://www.designworkplan.com/read/signage-and-color-contrast) -- 70% brightness differential threshold for assured legibility, Arthur & Passini 1992 method (MEDIUM confidence)
- [Best Color Combinations for Signs 2025](https://www.indigosigns.com/news/best-color-combinations-sign-2025-update) -- High-contrast pairing recommendations for LED displays (MEDIUM confidence)
- [About READMEs - GitHub Docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) -- README auto-rendering, naming, placement conventions (HIGH confidence)
- [Standard README](https://github.com/RichardLitt/standard-readme) -- Section structure and ordering conventions for GitHub READMEs (HIGH confidence)
- [iterate/olorm](https://github.com/iterate/olorm) -- Real Norwegian-language README using "Installasjon" terminology (MEDIUM confidence)
- [Color Difference - Wikipedia](https://en.wikipedia.org/wiki/Color_difference) -- Perceptual color distance theory, JND thresholds, CIE color spaces (HIGH confidence)
- Codebase analysis: `src/display/weather_anim.py` lines 79, 90 (rain drop colors), `src/display/layout.py` line 61 (`COLOR_WEATHER_RAIN`), `src/display/renderer.py` lines 196-202 (rain text rendering) -- actual color values causing the clash (HIGH confidence)
