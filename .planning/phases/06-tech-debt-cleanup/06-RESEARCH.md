# Phase 6: Tech Debt Cleanup - Research

**Researched:** 2026-02-21
**Domain:** Code cleanup and documentation debt (Python/Pillow project)
**Confidence:** HIGH

## Summary

This phase addresses 4 tech debt items identified in the v1.0 milestone audit, plus broader cleanup decided during phase discussion. The work is entirely code/documentation cleanup -- no new features, no behavior changes. All items are well-scoped: a dead constant to remove, a stale docstring to fix, a Pillow deprecation to remediate, and SUMMARY frontmatter to add.

Research confirms all items are straightforward. The Pillow deprecation (`Image.getdata()`) was deprecated in Pillow 12.1.0 (the project's currently installed version, 12.1.1) and has a drop-in replacement `get_flattened_data()`. The SUMMARY frontmatter addition is a structural change to 13 plan SUMMARY files requiring a requirements_completed field. Additional cleanup was identified: `PUSH_INTERVAL` is a dead constant in config.py (defined but never imported), and the main_loop docstring references `fonts["large"]` which was removed in Phase 5.

**Primary recommendation:** Handle all items in a single plan. Changes are small, independent, and non-breaking. Run the full test suite (96 tests) as verification after all changes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation details are at Claude's discretion.

### Claude's Discretion
- SUMMARY frontmatter format details (structure, duplication policy, empty handling)
- Pillow deprecation audit scope and verification approach
- Whether human verification items get a documentation note
- Whether to re-run milestone audit after completion

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.1 (installed) | Image processing (the deprecation target) | Project's primary rendering library |
| Python | 3.10+ | Runtime | Per pyproject.toml requires-python |
| pytest | (dev dep) | Test verification after changes | Already in dev dependencies |
| ruff | (dev dep) | Lint check after changes | Already in dev dependencies |

### Supporting
No new libraries needed. This is a cleanup-only phase using existing tools.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `get_flattened_data()` | `list(img.getdata())` pattern with numpy | Unnecessary complexity -- `get_flattened_data()` is the direct drop-in replacement |

**Installation:** No new packages needed.

## Architecture Patterns

### Pattern 1: Dead Code Removal
**What:** Remove constants from `src/config.py` that are defined but never imported by any module.
**When to use:** When a constant has zero `from src.config import X` references outside its definition file.
**Verification method:**
```bash
# Verify constant is unused before removal
grep -r "FONT_LARGE" src/ tests/ --include="*.py" | grep -v "config.py"
grep -r "PUSH_INTERVAL" src/ tests/ --include="*.py" | grep -v "config.py"
```

**Current dead constants in config.py:**

| Constant | Line | Defined As | Imported By | Status |
|----------|------|------------|-------------|--------|
| `FONT_LARGE` | 16 | `"7x13"` | Nobody (removed in Phase 5) | DEAD -- remove |
| `PUSH_INTERVAL` | 12 | `1` | Nobody (never used -- main loop uses hardcoded sleep values) | DEAD -- remove |
| `FONT_SMALL` | 17 | `"5x8"` | `src/main.py`, `tests/test_renderer.py` | ACTIVE |
| `FONT_TINY` | 18 | `"4x6"` | `src/main.py`, `tests/test_renderer.py` | ACTIVE |
| `FONT_DIR` | 15 | `PROJECT_ROOT / "assets" / "fonts"` | `src/main.py`, `tests/test_fonts.py`, `tests/test_renderer.py` | ACTIVE |
| All others | various | various | At least one import | ACTIVE |

### Pattern 2: Docstring Accuracy Fix
**What:** Update docstrings that reference removed code elements.
**Where:** `src/main.py` line 88 -- `main_loop()` docstring says `fonts["large", "small", "tiny"]` but the actual font dict only has `"small"` and `"tiny"` keys (since Phase 5 removed `fonts["large"]`).
**Fix:** Change `"large", "small", "tiny"` to `"small", "tiny"` in the docstring.

**Broader main.py docstring audit (per user request):**

| Function | Docstring | Accurate? | Issue |
|----------|-----------|-----------|-------|
| Module docstring (line 1-9) | "Renders a clock dashboard on the Pixoo 64 with Norwegian date formatting" | Partially stale | Does not mention bus, weather, or animation -- but acceptable as a brief summary |
| `build_font_map()` (line 55) | "Dictionary with keys 'small', 'tiny'" | Accurate | Updated in Phase 5 |
| `main_loop()` (line 77) | `fonts["large", "small", "tiny"]` | **STALE** | Should be `"small", "tiny"` |
| `main()` (line 252) | "Parse arguments and start the dashboard" | Accurate | No issues |

### Pattern 3: Pillow Deprecation Fix
**What:** Replace `Image.getdata()` calls with `get_flattened_data()`.
**Why:** `getdata()` was deprecated in Pillow 12.1.0 (released 2026-01-02). The project currently runs Pillow 12.1.1. The v1.0 audit referenced Pillow 14 (2027-10-15) as the removal date, but the deprecation is already active and producing warnings on the installed version.
**Replacement API:** `image.get_flattened_data(band=None)` -- identical signature, returns a tuple instead of an internal Pillow data type.

**All `getdata()` call sites in the project:**

| File | Line | Usage | Action |
|------|------|-------|--------|
| `tests/test_weather_anim.py` | 29 | `max(alpha_band.getdata())` | Replace with `max(alpha_band.get_flattened_data())` |
| `tests/test_weather_anim.py` | 38 | `sum(1 for a in alpha_band.getdata() if a > 0)` | Replace with `get_flattened_data()` |
| `tests/test_fonts.py` | 53 | `list(img.getdata())` | Replace with `list(img.get_flattened_data())` |

**Production code audit:** Zero `getdata()` calls in `src/` -- all 3 instances are in test files only. No other active Pillow deprecations affect this codebase (checked: `getbbox()` is current, no `getsize()`, no `Image._show`).

**pyproject.toml consideration:** Currently specifies `"Pillow"` with no version pin. The `get_flattened_data()` method requires Pillow >= 12.1.0. Adding a version floor (`"Pillow>=12.1.0"`) would be prudent to prevent breakage if someone installs an older version. However, this is optional -- the method is brand new and no older version would lack both old and new API.

### Pattern 4: SUMMARY Frontmatter Addition
**What:** Add a `requirements_completed` field to the YAML frontmatter of all 13 plan SUMMARY.md files.
**Why:** The v1.0 audit flagged this as a structural format gap -- no SUMMARY file tracks which requirement IDs were completed by that plan.

**Existing frontmatter convention** (from examining all 14 SUMMARY files):
```yaml
---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [pixoo, pillow, bdf-fonts, ...]

# Dependency graph
requires: [...]
provides: [...]
affects: [...]

# Tech tracking
tech-stack:
  added: [...]
  patterns: [...]

key-files:
  created: [...]
  modified: [...]
---
```

**Recommendation for `requirements_completed` field:**

Format: Simple YAML list of requirement IDs. Place it at the top of the frontmatter (after `tags:`) since it's a primary metadata field.

```yaml
requirements_completed: [DISP-01, DISP-02, DISP-03, CLCK-01, CLCK-02, RLBL-01]
```

**Duplication policy:** Allow a requirement ID to appear in multiple SUMMARYs when multiple plans contributed to satisfying it. The primary plan (where the implementation was done) is the canonical location, but a requirement that was started in one plan and extended/completed in another should appear in both. This matches how the traceability table in REQUIREMENTS.md works -- it maps to phases, not individual plans.

**Empty handling:** Plans with no associated requirements (e.g., 03-03 gap closure, 04-05 ad-hoc UAT, 05-01 verification) should use an empty list: `requirements_completed: []`. This makes it explicit that the plan was intentionally mapped.

**Requirement-to-plan mapping** (derived from REQUIREMENTS.md traceability + ROADMAP.md):

| SUMMARY File | Requirements |
|-------------|-------------|
| 01-01-SUMMARY.md | `[DISP-01, DISP-02, RLBL-01]` -- scaffolding, fonts, device driver, connection refresh |
| 01-02-SUMMARY.md | `[DISP-03, CLCK-01, CLCK-02]` -- layout, clock, Norwegian date |
| 02-01-SUMMARY.md | `[BUS-01, BUS-02, BUS-03, BUS-05]` -- bus provider, countdown, refresh |
| 02-02-SUMMARY.md | `[BUS-01, BUS-02, BUS-03, BUS-05]` -- bus renderer integration |
| 03-01-SUMMARY.md | `[WTHR-01, WTHR-03]` -- weather provider, temperature, high/low |
| 03-02-SUMMARY.md | `[WTHR-01, WTHR-02, WTHR-03, WTHR-04]` -- weather renderer, icon, rain indicator |
| 03-03-SUMMARY.md | `[]` -- gap closure (animation visibility fix, no new requirements) |
| 04-01-SUMMARY.md | `[BUS-04, RLBL-02]` -- urgency colors, staleness/error handling |
| 04-02-SUMMARY.md | `[DISP-04]` -- auto-brightness |
| 04-03-SUMMARY.md | `[MSG-01]` -- Discord message override |
| 04-04-SUMMARY.md | `[RLBL-03]` -- launchd service wrapper |
| 04-05-SUMMARY.md | `[]` -- ad-hoc UAT refinement (animation depth, no new requirements) |
| 05-01-SUMMARY.md | `[]` -- verification and cleanup (no new requirements, closed gaps) |

**Note:** The research SUMMARY at `.planning/research/SUMMARY.md` is not a plan SUMMARY and should be excluded from this change. It has no frontmatter and no plan number.

### Anti-Patterns to Avoid
- **Changing behavior while cleaning up:** All changes must be semantic no-ops. No test behavior changes, no API changes, no render changes.
- **Over-scoping the docstring review:** The user asked to check main.py docstrings broadly. The module docstring is slightly dated (mentions "clock dashboard" without bus/weather) but is acceptable as a brief summary. Only the `main_loop()` docstring with the stale `fonts["large"]` reference is a genuine fix target.
- **Version-pinning Pillow too tightly:** Adding `Pillow>=12.1.0` is reasonable. Adding `Pillow<14` would be overly defensive and likely wrong (14 will have the replacement API).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pillow pixel data access | Custom numpy/array conversion | `get_flattened_data()` | Direct API replacement, zero behavior change |
| YAML frontmatter editing | Custom YAML parser | Manual text editing (read file, find `---` delimiters, insert line) | The frontmatter is simple enough that a full YAML parser is overkill; just insert the line after `tags:` |

**Key insight:** Every change in this phase is a targeted text edit. No new abstractions, no new patterns, no new libraries.

## Common Pitfalls

### Pitfall 1: Breaking Test Assertions After getdata() Swap
**What goes wrong:** The return type of `get_flattened_data()` is a tuple, while `getdata()` returns an internal ImagingCore type. Code that depends on the specific type (isinstance checks, pickle, etc.) would break.
**Why it happens:** Assuming the return types are identical.
**How to avoid:** In this project, all 3 call sites use `getdata()` with iteration (`max()`, `sum()`, `list()`) -- both types are iterable, so the swap is safe. Run the test suite after the change to confirm.
**Warning signs:** Any test doing `type(data)` or `isinstance(data, ...)` checks -- none exist here.

### Pitfall 2: Forgetting PUSH_INTERVAL During config.py Cleanup
**What goes wrong:** Removing `FONT_LARGE` but leaving `PUSH_INTERVAL` (also dead).
**Why it happens:** The v1.0 audit only flagged `FONT_LARGE`. The user asked to scan config.py for other unused constants during phase discussion.
**How to avoid:** Verify every constant in config.py has at least one import outside config.py before declaring the cleanup complete.
**Warning signs:** Constants in config.py with zero grep hits in other `.py` files.

### Pitfall 3: Wrong Requirement IDs in SUMMARY Frontmatter
**What goes wrong:** Assigning a requirement to the wrong plan, causing traceability confusion.
**Why it happens:** Requirements often span multiple plans (provider plan + renderer plan). The mapping is not always 1:1.
**How to avoid:** Cross-reference the REQUIREMENTS.md traceability table (which maps to phases) and the ROADMAP.md (which lists requirements per phase) to determine which plans within a phase actually delivered the requirement.
**Warning signs:** A requirement appearing in a SUMMARY that never touched the requirement's subsystem.

### Pitfall 4: Editing the Research SUMMARY by Mistake
**What goes wrong:** Adding `requirements_completed` to `.planning/research/SUMMARY.md`, which is not a plan SUMMARY.
**Why it happens:** Glob pattern `**/*SUMMARY.md` matches 14 files, but only 13 are plan SUMMARYs.
**How to avoid:** Only edit files matching `XX-YY-SUMMARY.md` pattern (numeric phase-plan prefix). The research SUMMARY has no frontmatter and no plan number.

## Code Examples

### Replacing getdata() in test_weather_anim.py

**Before (deprecated):**
```python
def _max_alpha_in_frame(self, frame: Image.Image) -> int:
    """Return the maximum alpha value found in an RGBA frame."""
    alpha_band = frame.split()[3]
    return max(alpha_band.getdata())

def _count_non_transparent_pixels(self, frame: Image.Image) -> int:
    """Count pixels with alpha > 0."""
    alpha_band = frame.split()[3]
    return sum(1 for a in alpha_band.getdata() if a > 0)
```

**After (current API):**
```python
def _max_alpha_in_frame(self, frame: Image.Image) -> int:
    """Return the maximum alpha value found in an RGBA frame."""
    alpha_band = frame.split()[3]
    return max(alpha_band.get_flattened_data())

def _count_non_transparent_pixels(self, frame: Image.Image) -> int:
    """Count pixels with alpha > 0."""
    alpha_band = frame.split()[3]
    return sum(1 for a in alpha_band.get_flattened_data() if a > 0)
```

### Replacing getdata() in test_fonts.py

**Before:**
```python
pixels = list(img.getdata())
```

**After:**
```python
pixels = list(img.get_flattened_data())
```

### Removing Dead Constants from config.py

**Before:**
```python
PUSH_INTERVAL = 1  # seconds between state checks

# Font settings
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_LARGE = "7x13"   # for clock digits
FONT_SMALL = "5x8"    # for date and labels
FONT_TINY = "4x6"     # for zone labels
```

**After:**
```python
# Font settings
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_SMALL = "5x8"    # for date and labels
FONT_TINY = "4x6"     # for zone labels
```

Note: The `# for clock digits` comment on `FONT_LARGE` is also stale (clock now uses `FONT_SMALL`). Both the constant and its comment should go.

### Fixing main_loop() Docstring

**Before (line 88):**
```python
fonts: Font dictionary with keys "large", "small", "tiny".
```

**After:**
```python
fonts: Font dictionary with keys "small", "tiny".
```

### SUMMARY Frontmatter Addition Example

**Before (01-01-SUMMARY.md):**
```yaml
---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [pixoo, pillow, bdf-fonts, bitmap-fonts, norwegian, pil]
```

**After:**
```yaml
---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [pixoo, pillow, bdf-fonts, bitmap-fonts, norwegian, pil]
requirements_completed: [DISP-01, DISP-02, RLBL-01]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Image.getdata()` | `Image.get_flattened_data()` | Pillow 12.1.0 (2026-01-02) | Returns tuple instead of internal type; iterability preserved |
| `font.getsize()` | `font.getbbox()` / `font.getlength()` | Pillow 9.2.0 (2022) | Already migrated in this project -- no action needed |

**Deprecated/outdated:**
- `Image.getdata()`: Deprecated Pillow 12.1.0, removal date TBD (v1.0 audit referenced Pillow 14 / 2027-10-15). Replace with `get_flattened_data()`.

## Open Questions

1. **Should pyproject.toml pin Pillow >= 12.1.0?**
   - What we know: `get_flattened_data()` was added in 12.1.0. Current install is 12.1.1. No pin currently exists.
   - What's unclear: Whether the project will ever need to run on older Pillow. Unlikely given this is a personal project.
   - Recommendation: Add `"Pillow>=12.1.0"` as a floor pin. Low effort, prevents confusion if environment is recreated.

2. **Should a re-audit be run after this phase?**
   - What we know: The v1.0 audit found 7 items total. 3 are human verification (out of scope). 4 are code/doc items addressed here.
   - What's unclear: Whether the cleanup will introduce any new issues.
   - Recommendation: Do not run a full re-audit. A `ruff check src/` and full test suite run is sufficient verification. The changes are too small and well-understood to warrant a formal audit cycle.

3. **Should human verification items get a documentation note?**
   - What we know: 3 audit items are human verification (animation on hardware, weather refresh observation, launchd restart on target macOS). These are out of scope for this code-only phase.
   - Recommendation: No documentation note needed. They are already documented in the v1.0 audit report and visible to any future reader. Adding a separate note would be redundant.

## Sources

### Primary (HIGH confidence)
- Pillow 12.1.0 release notes: https://pillow.readthedocs.io/en/stable/releasenotes/12.1.0.html -- `getdata()` deprecation, `get_flattened_data()` replacement
- Pillow deprecations page: https://pillow.readthedocs.io/en/stable/deprecations.html -- full deprecation index
- Codebase inspection: `src/config.py`, `src/main.py`, `tests/test_weather_anim.py`, `tests/test_fonts.py` -- all findings verified by direct file reads

### Secondary (MEDIUM confidence)
- Pillow 14 removal timeline (2027-10-15) referenced in v1.0 audit -- not independently verified in current Pillow docs, which only say "deprecated" without explicit removal date. The 2027-10-15 date may be an estimate.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Dead code removal: HIGH -- verified by grep, zero imports found
- Docstring fix: HIGH -- exact line identified, exact stale text confirmed
- Pillow deprecation: HIGH -- verified against installed version 12.1.1, official docs confirm API
- SUMMARY frontmatter: HIGH -- all 13 files examined, requirement mapping derived from traceability table

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable -- no fast-moving dependencies)
