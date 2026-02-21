# Project Research Summary

**Project:** Divoom Hub v1.1 — Documentation & Polish
**Domain:** LED dashboard documentation and display color accessibility
**Researched:** 2026-02-21
**Confidence:** HIGH

## Executive Summary

Divoom Hub v1.1 is a tightly scoped polish milestone with exactly two deliverables: a Norwegian-language README and a weather animation color fix. Research across all four areas converges on the same conclusion — this is low-risk, well-understood work that requires no new dependencies, no architectural changes, and no new tooling. The existing Python/Pillow/pixoo stack is complete as-is. The entire code surface is five lines across two files (`layout.py`, `weather_anim.py`) plus a new `README.md`. Complexity is documentation quality and hardware color validation, not engineering.

The recommended build order is color fix first, README second. The color fix should inform the README's description of the animation system, and it requires physical Pixoo 64 hardware testing as the acceptance gate — not just unit tests. The core color problem is that rain indicator text (`COLOR_WEATHER_RAIN`) and rain animation particles share the same blue hue family, making the text invisible during rain. The fix requires coordinating particle and text colors as a unit: rain particles should be vivid blue, snow particles should be bright cool-white, and rain text should shift to bright white `(255, 255, 255)` — which provides maximum luminance contrast against every animation type and is the industry-standard choice for informational text on LED displays.

The Norwegian README has one clear risk: privacy. The project's `.env` file contains the user's home GPS coordinates, specific bus stop IDs, and Discord tokens. Example values in the README must use safe placeholders, not the real values. A pre-commit secrets grep is mandatory. Beyond that, the README work is straightforward: Norwegian Bokmal, shields.io badge for Claude Code attribution, standard GitHub README structure, no documentation generators, no dual-language maintenance burden.

## Key Findings

### Recommended Stack

No stack changes are needed for v1.1. The existing dependencies (Python 3.12+, Pillow >=12.1.0, pixoo, discord.py, python-dotenv) handle everything. The Norwegian README requires no tooling — GitHub renders UTF-8 Markdown natively, including ae/oe/aa. The Claude Code attribution badge is a static shields.io image link with no runtime dependency.

**Core technologies (unchanged from v1.0):**
- Python 3.12+: runtime — keep as-is, no version constraint changes needed
- Pillow >=12.1.0 (12.1.1 available): image rendering and RGBA compositing — version constraint already correct
- pixoo (unpinned): Pixoo 64 LAN communication — keep as-is
- discord.py >=2.0: message override bot — keep as-is
- pytest + ruff: test suite (96 tests) and linting — keep as-is

### Expected Features

**Must have (table stakes):**
- Prosjektbeskrivelse (project overview) — first thing readers see; photo of running display strongly recommended
- Installasjon + Oppsett (install and config) — clone to running in 5 minutes; reference `.env.example` for config table
- Bruk (usage) — document `--simulated`, `--save-frame`, and `TEST_WEATHER` env var
- Kjore som tjeneste (launchd service) — step-by-step from plist to `launchctl`
- Rain particle vs rain text distinguishability fix — primary reported hardware bug; blocks v1.1 completion
- Verification of all 8 animation types after color change — systematic check, not just rain

**Should have (differentiators):**
- "Bygget med Claude Code" badge and transparency section — explicitly requested in milestone; badge at top, methodology note in Utvikling section
- Skjermoppsett (zone layout diagram) — ASCII art of 64px budget makes the project tangible
- Arkitektur (module map + data flow) — providers -> DisplayState -> renderer -> pixoo; valuable for anyone forking
- API documentation (Entur + MET Norway) — gotchas like ET-Client-Name header, If-Modified-Since caching, rate limits
- Vaeranimasjoner (animation system description) — 3D depth layering, bg/fg compositing, 6 animation types
- Discord-meldinger, birthday easter egg, error resilience, Norwegian character support sections

**Defer (not in v1.1 scope):**
- English-language README alongside Norwegian — doubles maintenance, no benefit for a personal project
- Nynorsk variant — irrelevant for this project and user
- Auto-generated API reference (Sphinx/MkDocs) — over-engineering for 2,321 LOC project
- Configurable color palette — 1-2 constant changes is the right scope, not a configuration system
- Per-weather-condition text color overrides — adds complexity without gain

### Architecture Approach

v1.1 changes are entirely additive and non-breaking. The color fix touches the rendering layer only — fill color values in `weather_anim.py` and one constant in `layout.py`. The compositing pipeline itself (`_composite_layer()` in `renderer.py`) must not be touched; it was debugged and fixed in v1.0 and must remain isolated from color work. The README is a new file at the project root with zero code integration — it reads from the codebase but nothing reads it. Thunder animation inherits from `RainAnimation`, so rain particle color changes propagate to thunder automatically without a separate change.

**Components affected by v1.1:**
1. `src/display/weather_anim.py` — rain and snow particle fill colors (~4 lines in `tick()` methods)
2. `src/display/layout.py` — `COLOR_WEATHER_RAIN` constant (1 line)
3. `README.md` (new) — documentation file drawing on all existing modules as content sources

**Components that must NOT change:**
1. `renderer.py` `_composite_layer()` — working compositing logic, do not touch alongside color changes
2. `config.py`, `state.py`, providers — no scope for v1.1

### Critical Pitfalls

1. **Color fix creates new text/particle color collision** — If rain particles become vivid blue but rain text stays blue too, the original indistinguishability bug recurs in a different color. Choose particle and text colors as a coordinated palette: rain particles vivid blue, rain text bright white `(255, 255, 255)` for maximum contrast against every animation type. White has no conflict with blue rain, grey clouds, yellow sun, grey fog, or white snow (snow occupies different zone space).

2. **Color changes look correct on screen but fail on LED hardware** — PIL PNG previews on a monitor cannot validate LED rendering. LEDs have minimum brightness thresholds, non-linear brightness curves, and a different color gamut than LCD screens. Physical Pixoo 64 hardware testing is the only valid acceptance gate for color work. Do not sign off on color changes without viewing them on the actual device at 2+ meters.

3. **Alpha values must stay within empirically validated ranges** — The alpha ranges in `weather_anim.py` (bg_layer 40-100, fg_layer 90-200) were tuned specifically for LED visibility during v1.0 debugging. Change RGB channels only; do not adjust alpha values alongside color changes. Changing both simultaneously makes it impossible to isolate regressions.

4. **README exposes personal location data** — The user's real GPS coordinates, bus stop IDs (NSR:Quay:73154, NSR:Quay:73152), and Discord tokens must never appear in the README. Use explicit placeholders (`192.168.1.XXX`, `NSR:Quay:XXXXX`, Oslo city center `59.9139, 10.7522`). Grep the README against `.env` values before committing.

5. **Missing color regression tests** — Existing `test_weather_anim.py` tests check alpha thresholds only, not colors. After the fix, add color-identity assertions: rain particles must be blue-channel-dominant, snow particles must have roughly equal high RGB values (white-ish). Without these, a future change can silently revert the fix.

## Implications for Roadmap

Two clean, independent phases with a clear ordering rationale. All research points to this structure.

### Phase 1: Weather Color Fix

**Rationale:** Fix the code first, then document the fixed state. The README should describe how the animation system looks in its correct form. Hardware testing is the bottleneck; complete it while focused on code, before switching context to writing.

**Delivers:** Distinguishable rain, snow, and text colors on the physical Pixoo 64 display; color-identity test assertions that prevent future regression.

**Addresses:** Rain particle vs rain text indistinguishability (primary reported bug); snow vs rain visual distinction; systematic verification of all 8 animation types.

**Avoids:**
- Pitfall 1: Coordinate particle and text colors as a unit, not independently — rain particles blue, rain text white
- Pitfall 2: Physical hardware testing as acceptance gate — PNG previews are insufficient
- Pitfall 3: Keep alpha ranges unchanged; change RGB channels only
- Pitfall 5: Add color-identity tests in the same commit as the color fix

**Files changed:**
- `src/display/weather_anim.py` — RainAnimation and SnowAnimation fill colors (~4 lines)
- `src/display/layout.py` — `COLOR_WEATHER_RAIN` constant (1 line)
- `tests/test_weather_anim.py` — color-identity assertions (new)

**Research flag:** Standard patterns — no research needed. Color constants are fully audited, recommended values are clear, compositing architecture is well understood.

### Phase 2: Norwegian README

**Rationale:** Documentation of the fixed codebase. No code risk. The README reads from all existing source files as content, but modifies nothing. Can be iterated freely without risk of breaking functionality.

**Delivers:** Complete Norwegian-language README.md at the project root with Claude Code attribution badge and transparency section.

**Addresses:** All table-stakes documentation sections (overview, install, config, usage, launchd service) plus differentiator sections (architecture, APIs, Discord, animations, birthday easter egg, error resilience, Norwegian character support).

**Avoids:**
- Pitfall 4: Privacy — use placeholder values throughout, grep README against `.env` before committing
- Norwegian language pitfall: Keep English technical terms in English (API, LED, pip, Python, README, fork, commit); write descriptive text in idiomatic Bokmal
- Claude Code attribution pitfall: Frame as development methodology note, not a disclaimer; badge near top, detailed note in Utvikling section

**Files changed:**
- `README.md` (new file at project root)

**Research flag:** Standard patterns — no research needed. README structure, Norwegian Bokmal conventions, shields.io badge format, and anti-features (dual-language, Sphinx) are all clearly defined by research.

### Phase Ordering Rationale

- Color fix must precede README so the README documents the corrected animation system, not the broken one
- Color fix has a hardware testing dependency; front-loading it avoids a late-cycle context switch back to code after documentation is underway
- The two phases touch zero overlapping files — they could theoretically run in parallel, but sequential is safer given hardware testing is the bottleneck and the README should reference the fixed state
- No phase requires additional library research during planning; both are fully specified by existing codebase knowledge

### Research Flags

Phases needing deeper research during planning: None. Both phases are fully characterized by this research cycle.

Phases with standard patterns (skip research-phase): Both phases. The color constants approach, compositing constraints, README structure, and Norwegian documentation conventions are all established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Codebase directly audited; no new dependencies needed; version constraints verified against PyPI |
| Features | HIGH | Both features derived from existing codebase analysis and a user-reported hardware bug; scope is precise and bounded |
| Architecture | HIGH | All 17 source files read and analyzed; debug history consulted; exact line numbers identified for all changes |
| Pitfalls | HIGH | Pitfalls derive from actual codebase inspection, documented v1.0 debug sessions, and identified test suite gaps |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact rain text color needs hardware validation:** STACK.md recommends orange `(255, 140, 60)` while FEATURES.md recommends white `(255, 255, 255)`. White is the stronger recommendation (maximum contrast against every animation type, industry-standard LED signage choice), but validate on physical hardware in Phase 1 — do not resolve by analysis alone. The 4x6 tiny font used for rain text makes readability non-negotiable.
- **`COLOR_WEATHER_TEMP_NEG` cyan borderline case:** `(80, 200, 255)` could conflict with rain particles during sub-zero rain (sleet). STACK.md flags this as an edge case. Monitor during Phase 1 hardware testing; fix only if the problem is visible on the actual display.
- **Snow far flake color:** Current `(200, 210, 230, 90)` is grey-ish and may be indistinguishable from rain at a glance. ARCHITECTURE.md recommends `(220, 230, 255, 90)` (cool white). Include in the Phase 1 color audit alongside rain.

## Sources

### Primary (HIGH confidence)
- Codebase audit: all 17 source files directly read — color values, compositing pipeline, test suite gaps, exact line numbers
- `.planning/debug/weather-animation-too-subtle.md` — documented root cause analysis from v1.0 compositing debug session
- `.planning/todos/done/2026-02-20-weather-animation-and-rain-text-colors-indistinguishable.md` — user-reported bug with specific hardware symptoms
- `.env.example` and `.gitignore` — what is protected vs what would be exposed in README
- [About READMEs - GitHub Docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) — README rendering, naming, placement
- [Standard README](https://github.com/RichardLitt/standard-readme) — section structure and ordering conventions
- [Pillow 12.1.1 on PyPI](https://pypi.org/project/pillow/) — version verification
- [Shields.io Static Badge API](https://shields.io/badges) — badge format and Claude brand color `D97757`
- [Color Difference - Wikipedia](https://en.wikipedia.org/wiki/Color_difference) — perceptual color distance theory, JND thresholds

### Secondary (MEDIUM confidence)
- [LED Sign Color Combos for Visibility](https://www.ledsignsupply.com/designing-eye-catching-content-for-outdoor-led-signs/) — white/yellow on dark as top LED readability combinations
- [Signage and Color Contrast](https://www.designworkplan.com/read/signage-and-color-contrast) — 70% brightness differential threshold for assured legibility
- [Visme: Color Blind Friendly Palettes](https://visme.co/blog/color-blind-friendly-palette/) — blue-orange as safest color-blind-friendly pair
- [Smashing Magazine: Designing for Colorblindness](https://www.smashingmagazine.com/2024/02/designing-for-colorblindness/) — channel separation principles
- [iterate/olorm](https://github.com/iterate/olorm) — real Norwegian-language README using "Installasjon" terminology

### Tertiary (LOW confidence)
- [NRK Open Source](https://nrkno.github.io/) — Norwegian org README conventions (English default); limited sample size, inferred from pattern observation
- Norwegian documentation conventions via NAV GitHub organization — inferred from pattern observation

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
