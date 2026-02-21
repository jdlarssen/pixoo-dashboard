# Phase 5: Verification and Cleanup - Research

**Researched:** 2026-02-21
**Domain:** Process verification, test coverage, dead code removal
**Confidence:** HIGH

## Summary

Phase 5 is a procedural gap-closure phase, not a feature-building phase. The v1.0 milestone audit (2026-02-20) found that all 5 Phase 4 requirements are fully implemented and wired end-to-end, but the Phase 4 VERIFICATION.md artifact was never created. This single missing artifact causes 5 requirements (DISP-04, BUS-04, RLBL-02, RLBL-03, MSG-01) to show "partial" status in the audit. Additionally, the audit identified three tech debt items: a missing test for the staleness indicator dot, a dead `fonts["large"]` entry in `build_font_map()`, and unchecked REQUIREMENTS.md checkboxes.

All four success criteria are well-scoped, mechanically achievable, and require no external dependencies, no new libraries, and no design decisions. The work is entirely internal to the `.planning/` docs and existing test/source files.

**Primary recommendation:** Execute as a single plan with 4 tasks matching the 4 success criteria. Each task is independently verifiable.

## Standard Stack

### Core

No new libraries or tools required. Phase 5 operates entirely within the existing codebase.

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| pytest | (existing) | Run test suite to verify new staleness test | Already in pyproject.toml |
| PIL/Pillow | (existing) | Used by the staleness dot test to inspect rendered pixels | Already in pyproject.toml |

### Supporting

None needed.

### Alternatives Considered

None -- this phase has no technology choices to make.

## Architecture Patterns

### Pattern 1: VERIFICATION.md Structure (Established in Phases 1-3)

**What:** Each completed phase has a VERIFICATION.md file with YAML frontmatter, observable truths table, artifact inventory, key link verification, requirements coverage, anti-pattern scan, and test results.

**When to use:** Phase 4 needs this artifact created.

**Structure (derived from 01-VERIFICATION.md, 02-VERIFICATION.md, 03-VERIFICATION.md):**

```markdown
---
phase: 04-polish-and-reliability
verified: [timestamp]
status: passed
score: N/N must-haves verified
re_verification: false
human_verification: [if any]
---

# Phase 4: Polish and Reliability Verification Report

**Phase Goal:** [from ROADMAP.md]
**Verified:** [timestamp]
**Status:** passed
**Re-verification:** No

## Goal Achievement

### Observable Truths
| # | Truth | Status | Evidence |
|---|-------|--------|----------|

### Required Artifacts
| Artifact | Status | Exists | Substantive | Wired |

### Key Link Verification
| From | To | Via | Status | Evidence |

### Requirements Coverage
| Requirement | Source Plan(s) | Description | Status | Evidence |

### Anti-Patterns Found
[scan results]

### Human Verification Required
[if any items need physical device testing]

### Test Results
[pytest output summary]

### Code Quality
[ruff check results]
```

**Evidence locations for the 5 requirements:**

| REQ-ID | What to verify | Where evidence lives |
|--------|----------------|---------------------|
| DISP-04 | Auto-brightness based on time of day | `src/config.py`: `get_target_brightness()`, constants `BRIGHTNESS_NIGHT=20`, `BRIGHTNESS_DAY=100`, `BRIGHTNESS_DIM_START=21`, `BRIGHTNESS_DIM_END=6`. `src/main.py` lines 203-208: brightness tracking in main loop. |
| BUS-04 | Color coding by urgency (green/yellow/red) | `src/display/layout.py`: `urgency_color()` function with 4 thresholds. `src/display/renderer.py`: `_draw_bus_line()` calls `urgency_color(departures[i])` per departure. |
| RLBL-02 | Graceful error states (show last known data when API fails) | `src/main.py` lines 119-199: `last_good_bus`, `last_good_weather` preservation, staleness flags. `src/display/renderer.py` lines 419-420, 432-433: orange dot indicators. `src/display/state.py`: `bus_stale`, `bus_too_old`, `weather_stale`, `weather_too_old` fields. |
| RLBL-03 | Auto-restart via service wrapper | `com.divoom-hub.dashboard.plist`: `RunAtLoad=true`, `KeepAlive/SuccessfulExit=false`. Installation instructions in XML comments. |
| MSG-01 | Push text message to temporarily override display | `src/providers/discord_bot.py`: `MessageBridge` (thread-safe), `run_discord_bot()`, `start_discord_bot()`. `src/display/renderer.py`: `_render_message()`, `_wrap_text()`. `src/display/state.py`: `message_text` field. `src/main.py` lines 211, 282-287: bridge integration. |

### Pattern 2: Staleness Dot Test (Missing Coverage)

**What:** The staleness indicator is an orange dot rendered at pixel (62, BUS_ZONE.y + 1) for bus and (62, WEATHER_ZONE.y + 1) for weather, controlled by the `bus_stale`/`weather_stale` flags on `DisplayState`. The dot renders only when `stale=True` AND `too_old=False`.

**Key renderer code (renderer.py lines 419-420, 432-433):**

```python
# Bus staleness dot
if state.bus_stale and not state.bus_too_old:
    draw.point((62, BUS_ZONE.y + 1), fill=COLOR_STALE_INDICATOR)

# Weather staleness dot
if state.weather_stale and not state.weather_too_old:
    draw.point((62, WEATHER_ZONE.y + 1), fill=COLOR_STALE_INDICATOR)
```

**Test approach:** Create `DisplayState` with `bus_stale=True` and render. Check pixel at (62, 21) for `COLOR_STALE_INDICATOR = (255, 100, 0)`. Repeat for weather staleness at (62, 41). Also verify dot is absent when `stale=False` (negative test) and absent when `too_old=True` (suppression test).

**Zone positions (from layout.py):**
- `BUS_ZONE.y = 20`, so staleness dot is at (62, 21)
- `WEATHER_ZONE.y = 40`, so staleness dot is at (62, 41)
- `COLOR_STALE_INDICATOR = (255, 100, 0)` -- orange

### Pattern 3: Dead Code Removal (fonts["large"])

**What:** `build_font_map()` in `src/main.py` line 66 loads `fonts["large"]` (7x13 BDF font). The renderer no longer uses this font -- it was changed from 7x13 to 5x8 in Plan 04-02 (clock font change). Only `fonts["small"]` and `fonts["tiny"]` are referenced in `renderer.py`.

**Scope of change:**
1. `src/main.py` line 66: Remove `"large": raw_fonts[FONT_LARGE]` from `build_font_map()`
2. `src/main.py` line 30: Remove `FONT_LARGE` import (no longer needed)
3. `src/config.py` line 16: `FONT_LARGE = "7x13"` -- KEEP. The font file still exists in `assets/fonts/` and is loaded by `load_fonts()` which scans all BDF files. The config constant is a declaration, not active code.
4. `tests/test_renderer.py` line 15: Remove `"large": _raw_fonts[FONT_LARGE]` from test FONTS dict
5. `tests/test_renderer.py` line 7: Remove `FONT_LARGE` from import

**Risk:** LOW. The renderer never accesses `fonts["large"]`. Removing it cannot break any code path. The `render_frame()` docstring mentions `"large"` in the fonts dict arg description -- this should be updated too.

**Note about FONT_LARGE constant in config.py:** The constant is a naming convention for the 7x13 font. It could be removed since nothing uses it, but it's also harmless to keep. Recommend removing it cleanly along with the rest, since `load_fonts()` returns all fonts by filename anyway. However, this is optional -- the audit only flagged the `build_font_map()` entry.

### Anti-Patterns to Avoid

- **Verification theater:** Don't write "VERIFIED" without actually checking the code. Each verification claim must cite specific file/line/function evidence.
- **Test that doesn't test:** The staleness dot test must assert on the exact pixel color at the exact coordinate, not just "zone has non-black pixels."
- **Cascading changes:** When removing `fonts["large"]`, don't also refactor unrelated code. Keep changes minimal and scoped to the audit findings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VERIFICATION.md format | A new format | Exact same structure as 01/02/03-VERIFICATION.md | Consistency with existing phases |
| Pixel color assertion | Complex pixel scanning | Direct `img.getpixel((x, y))` comparison | Single pixel at known coordinate |

**Key insight:** This is a cleanup phase. The implementations are complete. The work is documentation, testing, and minor code cleanup -- not building new features.

## Common Pitfalls

### Pitfall 1: Stale Evidence References

**What goes wrong:** Verification cites line numbers or behaviors that have changed since the SUMMARY was written (due to post-UAT 04-05 changes).
**Why it happens:** Plan 04-05 modified renderer.py, layout.py, and weather_anim.py extensively after Plans 01-04.
**How to avoid:** Verify evidence against the CURRENT codebase, not the SUMMARY descriptions. Re-read source files before writing evidence.
**Warning signs:** Line numbers from SUMMARY don't match current file.

### Pitfall 2: Test Position Hardcoding

**What goes wrong:** Test assumes pixel position that changes if layout.py zones are adjusted.
**Why it happens:** Zone positions are constants but could change in future.
**How to avoid:** Import `BUS_ZONE` and `WEATHER_ZONE` from layout.py and compute dot position as `(62, ZONE.y + 1)` rather than hardcoding `(62, 21)`.
**Warning signs:** Test fails after zone height changes.

### Pitfall 3: Incomplete Checkbox Update

**What goes wrong:** REQUIREMENTS.md checkboxes updated but traceability table status not updated.
**Why it happens:** The traceability table has its own Status column separate from the checkboxes.
**How to avoid:** Update BOTH: (1) checkbox `[ ]` to `[x]` AND (2) traceability table Status from "Pending" to "Complete".
**Warning signs:** Audit still shows "partial" after checkbox update.

### Pitfall 4: fonts["large"] Removal Missing Test File

**What goes wrong:** `build_font_map()` cleaned but `test_renderer.py` still loads and references `FONT_LARGE`.
**Why it happens:** Test file independently constructs a FONTS dict with the same `"large"` key.
**How to avoid:** Remove `"large"` from both `build_font_map()` AND the test file's FONTS dict. Update docstring in `render_frame()`.
**Warning signs:** Import of `FONT_LARGE` remains in test file after cleanup.

## Code Examples

### Staleness Dot Test

```python
# Source: Derived from existing test patterns in test_renderer.py
from src.display.layout import BUS_ZONE, WEATHER_ZONE, COLOR_STALE_INDICATOR

def test_bus_staleness_dot_renders_when_stale(self):
    """Orange dot appears at (62, BUS_ZONE.y+1) when bus_stale=True."""
    state = DisplayState(
        time_str="14:32",
        date_str="lor 21. mar",
        bus_direction1=(5, 12, 25),
        bus_direction2=(3, 8, 18),
        bus_stale=True,
        bus_too_old=False,
    )
    frame = render_frame(state, FONTS)
    pixel = frame.getpixel((62, BUS_ZONE.y + 1))
    assert pixel == COLOR_STALE_INDICATOR, (
        f"Expected orange dot {COLOR_STALE_INDICATOR} at (62, {BUS_ZONE.y + 1}), got {pixel}"
    )

def test_bus_staleness_dot_absent_when_not_stale(self):
    """No orange dot when bus_stale=False."""
    state = DisplayState(
        time_str="14:32",
        date_str="lor 21. mar",
        bus_direction1=(5, 12, 25),
        bus_direction2=(3, 8, 18),
        bus_stale=False,
    )
    frame = render_frame(state, FONTS)
    pixel = frame.getpixel((62, BUS_ZONE.y + 1))
    assert pixel != COLOR_STALE_INDICATOR, (
        f"Orange dot should not appear when bus_stale=False"
    )

def test_bus_staleness_dot_absent_when_too_old(self):
    """No orange dot when bus_too_old=True (even if stale=True)."""
    state = DisplayState(
        time_str="14:32",
        date_str="lor 21. mar",
        bus_stale=True,
        bus_too_old=True,
    )
    frame = render_frame(state, FONTS)
    pixel = frame.getpixel((62, BUS_ZONE.y + 1))
    assert pixel != COLOR_STALE_INDICATOR, (
        f"Orange dot should not appear when bus_too_old=True"
    )
```

### Dead Code Removal in build_font_map()

```python
# BEFORE (current):
def build_font_map(font_dir: str) -> dict:
    raw_fonts = load_fonts(font_dir)
    return {
        "large": raw_fonts[FONT_LARGE],  # DEAD - never used by renderer
        "small": raw_fonts[FONT_SMALL],
        "tiny": raw_fonts[FONT_TINY],
    }

# AFTER (cleaned):
def build_font_map(font_dir: str) -> dict:
    raw_fonts = load_fonts(font_dir)
    return {
        "small": raw_fonts[FONT_SMALL],
        "tiny": raw_fonts[FONT_TINY],
    }
```

### REQUIREMENTS.md Checkbox Update

```markdown
# BEFORE:
- [ ] **DISP-04**: Auto-brightness based on time of day
- [ ] **BUS-04**: Color coding by urgency (green/yellow/red)
- [ ] **RLBL-02**: Graceful error states (show last known data when API fails)
- [ ] **RLBL-03**: Auto-restart via service wrapper (systemd/launchd)
- [ ] **MSG-01**: Push text message to temporarily override display

# AFTER:
- [x] **DISP-04**: Auto-brightness based on time of day
- [x] **BUS-04**: Color coding by urgency (green/yellow/red)
- [x] **RLBL-02**: Graceful error states (show last known data when API fails)
- [x] **RLBL-03**: Auto-restart via service wrapper (systemd/launchd)
- [x] **MSG-01**: Push text message to temporarily override display
```

Also update the traceability table:

```markdown
# BEFORE:
| DISP-04 | Phase 5 | Pending |
| BUS-04 | Phase 5 | Pending |
| RLBL-02 | Phase 5 | Pending |
| RLBL-03 | Phase 5 | Pending |
| MSG-01 | Phase 5 | Pending |

# AFTER:
| DISP-04 | Phase 5 | Complete |
| BUS-04 | Phase 5 | Complete |
| RLBL-02 | Phase 5 | Complete |
| RLBL-03 | Phase 5 | Complete |
| MSG-01 | Phase 5 | Complete |
```

## State of the Art

Not applicable. This is a project-internal cleanup phase with no external technology dependencies.

## Open Questions

1. **Should `FONT_LARGE` constant be removed from `config.py`?**
   - What we know: The constant is unused after removing `build_font_map()` references. However, `load_fonts()` still loads the 7x13 font file (it scans all BDF files in the directory). The constant is inert.
   - What's unclear: Whether future phases might use it.
   - Recommendation: Remove it for cleanliness. The 7x13 BDF file remains in `assets/fonts/` and can be re-declared if ever needed. However, this is outside the audit's scope -- the audit only flags the `build_font_map()` entry. Keep or remove at Claude's discretion.

2. **Should the render_frame() docstring be updated?**
   - What we know: The docstring says `fonts: Dictionary with keys "large", "small", "tiny"` but "large" is no longer used.
   - Recommendation: Yes, update the docstring to match reality (`"small"` and `"tiny"` only).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISP-04 | Auto-brightness based on time of day | VERIFICATION.md evidence: `get_target_brightness()` in config.py, brightness tracking in main loop (lines 203-208). Implementation confirmed in 04-02-SUMMARY. |
| BUS-04 | Color coding by urgency (green/yellow/red) | VERIFICATION.md evidence: `urgency_color()` in layout.py, per-departure coloring in `_draw_bus_line()`. Implementation confirmed in 04-01-SUMMARY. |
| RLBL-02 | Graceful error states (show last known data when API fails) | VERIFICATION.md evidence: last-good preservation in main.py, staleness flags in state.py, orange dot indicators in renderer.py. Staleness dot test provides missing coverage. Implementation confirmed in 04-01-SUMMARY. |
| RLBL-03 | Auto-restart via service wrapper (systemd/launchd) | VERIFICATION.md evidence: `com.divoom-hub.dashboard.plist` with RunAtLoad + KeepAlive/SuccessfulExit=false. Implementation confirmed in 04-04-SUMMARY. |
| MSG-01 | Push text message to temporarily override display | VERIFICATION.md evidence: Discord bot provider, MessageBridge thread-safe pattern, message overlay rendering. Implementation confirmed in 04-03-SUMMARY. |
</phase_requirements>

## Sources

### Primary (HIGH confidence)

All findings are derived from direct codebase inspection of the Divoom Hub project:

- `src/display/renderer.py` -- Staleness dot rendering (lines 419-420, 432-433), render_frame() structure
- `src/display/layout.py` -- Zone positions, color constants, urgency_color() function
- `src/config.py` -- get_target_brightness(), FONT_LARGE, brightness constants
- `src/main.py` -- build_font_map(), staleness tracking, brightness scheduling
- `src/display/state.py` -- DisplayState fields including staleness flags
- `src/providers/discord_bot.py` -- MessageBridge, run_discord_bot(), start_discord_bot()
- `com.divoom-hub.dashboard.plist` -- launchd service definition
- `tests/test_renderer.py` -- Existing test patterns, FONTS dict with dead "large" entry
- `.planning/phases/01-foundation/01-VERIFICATION.md` -- Verification format reference
- `.planning/phases/02-bus-departures/02-VERIFICATION.md` -- Verification format reference
- `.planning/phases/03-weather/03-VERIFICATION.md` -- Verification format reference
- `.planning/phases/04-polish-and-reliability/04-*-SUMMARY.md` -- Phase 4 completion evidence
- `.planning/v1.0-MILESTONE-AUDIT.md` -- Gap identification source
- `.planning/REQUIREMENTS.md` -- Checkbox and traceability table current state

### Secondary (MEDIUM confidence)

None needed -- all evidence is first-party from the codebase.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new technology, entirely internal cleanup
- Architecture: HIGH -- VERIFICATION.md format is established across 3 prior phases
- Pitfalls: HIGH -- all pitfalls are derived from direct observation of current code and audit findings

**Research date:** 2026-02-21
**Valid until:** No expiration -- this is project-internal documentation, not dependent on external APIs or libraries
