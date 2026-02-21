# Stack Research

**Domain:** LED dashboard documentation and color accessibility (v1.1 milestone)
**Researched:** 2026-02-21
**Confidence:** HIGH

## Executive Finding

No new dependencies are needed for v1.1. The Norwegian README is a pure Markdown authoring task. The weather particle color fix is a constants-only change in `layout.py` and `weather_anim.py`. The existing stack (Python 3.12+, Pillow, pixoo) handles everything required.

## Existing Stack (Validated -- No Changes Needed)

### Core Technologies

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.12+ (venv runs 3.14) | Runtime | Keep as-is |
| Pillow | >=12.1.0 (latest: 12.1.1) | Image rendering, RGBA compositing | Keep as-is, version constraint already correct |
| pixoo | latest | Device communication over LAN | Keep as-is |
| discord.py | >=2.0 | Message override bot | Keep as-is |
| python-dotenv | >=1.0 | .env config loading | Keep as-is |

### Dev Dependencies

| Tool | Purpose | Status |
|------|---------|--------|
| pytest | Test suite (96 tests) | Keep as-is |
| ruff | Linting, line-length=100 | Keep as-is |

## Feature 1: Norwegian README

### What's Needed: Nothing New

The README is a single `README.md` file written in Norwegian Bokmal. This requires no tooling, no libraries, and no build steps. GitHub renders Markdown natively with full UTF-8 support for Norwegian characters (ae, oe, aa).

### README Structure Decisions

| Decision | Recommendation | Why |
|----------|---------------|-----|
| Language | Norwegian Bokmal | User preference, matches the dashboard's Norwegian date display. All code comments are English, so international developers can still navigate the codebase. |
| File name | `README.md` (root) | GitHub convention. Single README, no need for separate `README.no.md` / `README.en.md` since this is a personal project. |
| Encoding | UTF-8 (default) | GitHub and all modern editors handle this natively. No BOM needed. |

### Claude Code Transparency Badge

Use a shields.io static badge. No dependency, just a Markdown image link.

```markdown
![Bygd med Claude Code](https://img.shields.io/badge/Bygd%20med-Claude%20Code-D97757?logo=claude&logoColor=white)
```

The color `D97757` is Anthropic's official Claude brand color. The badge text "Bygd med" is Norwegian for "Built with".

**Source:** [Shields.io Static Badge API](https://shields.io/badges) -- HIGH confidence

### Norwegian README Conventions

No formal Norwegian-specific README standard exists (confirmed via search). Norwegian open source projects (e.g., NRK) typically write READMEs in English for broader reach. Since this is a personal/hobby project targeting a Norwegian household, writing in Bokmal is the right call. Follow standard GitHub README structure adapted to Norwegian:

| Section (Norwegian) | Purpose |
|---------------------|---------|
| Oversikt | Project overview with photo/screenshot |
| Funksjoner | Feature list |
| Oppsett | Installation and setup |
| Konfigurasjon | .env configuration reference |
| Arkitektur | System architecture overview |
| API-er | Entur and MET Norway API details |
| Tjeneste | launchd service setup |
| Discord | Message override feature |
| Utvikling | Development setup, testing |
| Bygd med Claude Code | AI transparency section |

## Feature 2: Weather Particle Color Fix

### The Problem

The current color assignments create indistinguishable elements on the Pixoo 64 LED hardware:

| Element | Current Color (RGB) | Visual Result |
|---------|---------------------|---------------|
| Rain text (`COLOR_WEATHER_RAIN`) | `(50, 180, 255)` | Blue |
| Rain far drops (bg) | `(40, 90, 200, 100)` | Blue |
| Rain near drops (fg) | `(60, 140, 255, 200)` | Blue |

All three are blue-channel-dominant. On a 64x64 LED matrix, the rain precipitation text ("2.5mm") bleeds into rain drop particles because they share the same hue. The text becomes invisible during rain animation.

### What's Needed: Color Constant Changes Only

This is a pure code change in two files:
- `src/display/layout.py` -- change `COLOR_WEATHER_RAIN`
- `src/display/weather_anim.py` -- potentially adjust particle colors

No new libraries or dependencies required. PIL/Pillow's RGBA compositing already handles alpha blending correctly.

### Recommended Color Palette Fix

The fix strategy is to separate text and animation into distinct color channels so they remain distinguishable even when overlapping via alpha compositing.

**Principle:** Text uses warm/hot colors (yellow, orange, white). Animations use cool colors (blue for rain, white for snow). This creates channel separation that survives alpha blending on LED hardware.

#### Current Problem Colors

```
Rain text:       (50, 180, 255)   -- blue, same hue as rain drops
Rain particles:  (40-60, 90-140, 200-255) -- blue
```

#### Recommended Fix

| Element | Current | Proposed | Why |
|---------|---------|----------|-----|
| `COLOR_WEATHER_RAIN` (text) | `(50, 180, 255)` blue | `(255, 140, 60)` orange | Warm color contrasts against cool blue rain particles. Orange is highly visible on LED. Blue-orange is the safest color-blind-friendly pair. |
| Rain far drops (bg) | `(40, 90, 200, 100)` | Keep as-is | Blue rain drops are visually correct for rain. The problem is the TEXT color matching, not the particle color. |
| Rain near drops (fg) | `(60, 140, 255, 200)` | Keep as-is | Same reasoning. |

**Why orange for rain text:**
1. **Channel separation:** Orange (R=255, G=140, B=60) is red-channel-dominant. Rain particles (B=200-255) are blue-channel-dominant. They cannot blend into each other on LED hardware.
2. **Color-blind safe:** Blue + orange is the recommended color-blind-friendly pair. It works for deuteranopia (red-green, 8% of men), protanopia (red-green, 1%), and tritanopia (blue-yellow, <0.01%).
3. **Consistent with existing palette:** `COLOR_BUS_DIR2` already uses `(255, 180, 50)` amber/orange, proving this hue works on the Pixoo 64 hardware.
4. **LED brightness:** Orange requires high R and moderate G values, both of which LED matrices render brightly.

**Confidence:** HIGH -- Based on established color theory (channel separation), confirmed LED behavior from v1.0 development (alpha values 65-180 range), and the project's own validated color palette.

#### Snow Animation Consideration

Snow particles are white `(200-255, 210-255, 230-255)`. The temperature text `COLOR_WEATHER_TEMP` is warm yellow `(255, 200, 50)` -- already distinct from white. The high/low text `COLOR_WEATHER_HILO` is teal `(120, 180, 160)` -- also distinct. No snow color changes needed.

#### Full Weather Zone Color Audit

| Element | Color | Channel Dominance | Conflict? |
|---------|-------|-------------------|-----------|
| Temp text (positive) | `(255, 200, 50)` | Red/Yellow | No -- distinct from all animations |
| Temp text (negative) | `(80, 200, 255)` | Cyan-Blue | Potential conflict with rain drops |
| Hi/Lo text | `(120, 180, 160)` | Teal/Green | No -- distinct channel |
| Rain text | `(50, 180, 255)` | **Blue -- CONFLICTS with rain** | **YES -- fix to orange** |
| Rain bg particles | `(40, 90, 200)` | Blue | No -- this is correct for rain |
| Rain fg particles | `(60, 140, 255)` | Blue | No -- this is correct for rain |
| Snow bg particles | `(200, 210, 230)` | White/cool | No -- temp text is yellow, distinct |
| Snow fg crystals | `(255, 255, 255)` | Pure white | No -- temp text is yellow, distinct |
| Sun rays | `(220-255, 180-230, 60-90)` | Yellow/Gold | Minor overlap with temp text, but sun + temp together is visually coherent |

**Secondary fix to consider:** `COLOR_WEATHER_TEMP_NEG` at `(80, 200, 255)` is cyan-blue, which could conflict with rain particles during sub-zero rain (sleet). Consider shifting to a lighter cyan like `(100, 220, 255)` or keeping as-is since sleet + negative temp is a narrow edge case. Flag for testing on hardware.

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| Documentation generators (Sphinx, MkDocs) | This is a single README for a personal project, not a library with API docs | Write `README.md` directly in Markdown |
| i18n/l10n libraries | Single language (Norwegian), no runtime translation needed | Hardcode Norwegian text in README |
| Color palette libraries (colorspacious, etc.) | The fix is 1-2 RGB constant changes, not a dynamic palette system | Hand-pick colors based on channel separation |
| Image generation for README screenshots | Screenshots should be actual photos of the display running, not generated images | Take a photo of the physical Pixoo 64 |
| Markdown linting (markdownlint, etc.) | Over-engineering for a single file | Review manually or use editor's built-in preview |
| Additional fonts or rendering libraries | BDF bitmap fonts already handle Norwegian characters | No changes to font pipeline |

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Orange rain text `(255, 140, 60)` | Green rain text `(50, 255, 100)` | Green conflicts with `COLOR_URGENCY_GREEN` in the bus zone above. While different zones, visual consistency matters. |
| Orange rain text `(255, 140, 60)` | White rain text `(255, 255, 255)` | White conflicts with snow particles. Rain and snow share the `sleet` mapping, so rain text could appear during snow animation. |
| Orange rain text `(255, 140, 60)` | Magenta rain text `(255, 80, 200)` | Magenta is not in the existing palette vocabulary. Orange already has precedent (bus direction 2). |
| Single README.md in Norwegian | README.md (EN) + README.no.md (NO) | Personal project, single audience. Dual READMEs add maintenance burden with no benefit. |
| shields.io static badge | Custom SVG badge | shields.io is the GitHub standard. No reason to custom-build. |

## Installation

No new packages to install. The existing `pyproject.toml` already covers everything:

```bash
# Already works -- no changes needed
pip install -e .
pip install -e ".[dev]"
```

## Version Compatibility

| Package | Current Constraint | Latest Available | Notes |
|---------|-------------------|------------------|-------|
| Pillow | >=12.1.0 | 12.1.1 | Compatible, minor patch. No action needed. |
| discord.py | >=2.0 | 2.x | Compatible. |
| python-dotenv | >=1.0 | 1.x | Compatible. |
| pixoo | (unpinned) | latest | No version constraint in pyproject.toml. Works as-is. |

## Files That Will Change

For the roadmap's benefit, here are the exact files impacted by each feature:

### Norwegian README
- **New:** `README.md` (project root)
- No other file changes

### Weather Color Fix
- **Modified:** `src/display/layout.py` -- change `COLOR_WEATHER_RAIN` constant
- **Possibly modified:** `src/display/weather_anim.py` -- only if particle colors also need adjustment (likely not)
- **Modified:** Tests that assert on `COLOR_WEATHER_RAIN` value (if any)

## Sources

- [Pillow 12.1.1 on PyPI](https://pypi.org/project/pillow/) -- version verification, HIGH confidence
- [Shields.io Static Badge API](https://shields.io/badges) -- badge format and Claude brand color, HIGH confidence
- [Visme: Color Blind Friendly Palettes](https://visme.co/blog/color-blind-friendly-palette/) -- blue-orange as safest pair, MEDIUM confidence
- [Smashing Magazine: Designing for Colorblindness](https://www.smashingmagazine.com/2024/02/designing-for-colorblindness/) -- channel separation principles, MEDIUM confidence
- [NRK Open Source](https://nrkno.github.io/) -- Norwegian org README conventions (English default), LOW confidence (limited sample)
- Codebase analysis of `src/display/layout.py` and `src/display/weather_anim.py` -- color audit, HIGH confidence (primary source)

---
*Stack research for: Divoom Hub v1.1 (Documentation & Polish)*
*Researched: 2026-02-21*
