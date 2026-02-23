# Project Research Summary

**Project:** Divoom Hub v1.2 — Sun Ray Overhaul
**Domain:** LED pixel display animation (Pixoo 64 weather dashboard)
**Researched:** 2026-02-23
**Confidence:** HIGH

## Executive Summary

The v1.2 Sun Ray Overhaul is a tightly scoped refactor of a single animation class (`SunAnimation` in `weather_anim.py`) to replace random sky-wide diagonal rays with radial emission from a visible half-sun body. The core problem is well-diagnosed: the existing animation looks like "yellow diagonal rain" because rays spawn at random positions with no spatial connection to the sun. The fix is conceptually straightforward — move the sun to the top edge of the weather zone, make it a semicircle clipped at y=0, and emit rays outward from its center using polar coordinates with distance-based alpha fade. No new dependencies are needed; Python's `math` stdlib and Pillow 12.1.1 already provide every required primitive.

The recommended approach is test-first in three sequential phases: establish the half-sun body geometry first (it sets the origin for all rays), then replace the ray system with polar-to-cartesian emission, then tune parameters through hardware testing. The two-layer `(bg, fg)` RGBA compositing contract that drives the rendering pipeline is completely unchanged — only `SunAnimation`'s internals are rewritten. The total scope is approximately 90 lines of production code change and 40 lines of test updates across exactly 2 files.

The key risks are concentrated in the ray implementation phase, not the architecture. Alpha fade math that looks correct in PNG test output can fail on LED hardware because LEDs have a hard minimum brightness floor (~RGB 15,15,15). The proposed linear fade formula will make far rays invisible before they reach `MAX_DIST`, creating ghost rays and an apparent "halo boundary." An off-by-one rounding choice (`int()` vs `round()`) in polar-to-pixel conversion introduces a systematic directional bias across all 14 rays. Both risks are one-line fixes once understood — the danger is implementing them incorrectly and not catching them until physical hardware testing.

## Key Findings

### Recommended Stack

The existing stack is exactly right and needs zero changes. Pillow 12.1.1 provides `pieslice()` for the semicircle body and `point()`/`line()` for rays with RGBA fills. Python's `math` stdlib provides `cos`, `sin`, and `radians` — all already imported in `weather_anim.py`. Performance is a non-issue: 14 rays at 15px length draw in 0.02ms per tick against a 1000ms frame budget (0.002% utilization).

**Core technologies:**
- **Python 3.14 + `math` stdlib**: Polar-to-cartesian conversion — already imported, no changes needed
- **Pillow 12.1.1**: `pieslice()` for half-sun body, `line()` for rays, RGBA alpha compositing — already installed, verified against this version
- **`random` stdlib**: Ray angle and speed randomization on spawn/respawn — already imported

**Critical version note:** `pieslice()` with RGBA fill has been available since Pillow 2.0+. The current `Pillow>=12.1.0` constraint in `pyproject.toml` is correct and requires no change.

### Expected Features

The feature set is driven by one user requirement: sun rays must be recognizable as sunshine, not random streaks. All table stakes features have clear implementation paths.

**Must have (table stakes):**
- **Half-sun body at zone top edge** — without a visible sun, rays look like abstract lines; semicircle at (48, 0) r=7 via Pillow auto-clipping
- **Rays originate from sun center** — radial emission from (48, 0) using polar coordinates; this is the single fix for the core bug
- **Distance-based alpha fade** — linear falloff `alpha = base_alpha * (1 - dist/max_dist)`; makes beams look like light rather than particles
- **Ray respawn at sun origin** — continuous animation; rays recycled to sun center on exit or fade-out
- **Two-depth-layer system preserved** — far rays (9) on bg behind text, near rays (5) on fg in front; existing `(bg, fg)` contract unchanged
- **Yellow color palette maintained** — far (240,200,40), near (255,240,60), body (255,220,60); matches dashboard visual language
- **Tests pass for new geometry** — TestSunBody coordinate assertions updated for new position and radius

**Should have (differentiators):**
- **Staggered initial ray distances** — animation starts mid-flow, not as a burst; use `random.uniform(0, MAX_DIST * 0.7)` on init
- **Variable ray length per ray** — organic quality; 2-4px far, 4-7px near; already specified in spawn parameters
- **Angle range avoids pure horizontal** — 0.15pi to 0.85pi prevents near-horizontal rays that flicker and exit quickly
- **Ray origin clustering test** — regression gate: asserts rays cluster near sun position on first tick

**Defer (post-v1.2):**
- Dynamic ray count based on weather intensity (no intensity parameter exists for clear sky)
- Sunrise/sunset color transitions (belongs in a new animation class, not this one)
- Sun body position varying with time (zone too small for meaningful motion)
- Wind effect on sun rays (polar coordinate rays cannot meaningfully receive cartesian wind offsets)

### Architecture Approach

The change is entirely contained within `SunAnimation`. The external interface — `tick()` returning `(bg_layer, fg_layer)` as RGBA 64x24 images — is unchanged. The renderer, main loop, factory function, and all other animation classes are untouched. The key internal changes are: (1) ray data structure changes from `list[float]` with positional indexing to `dict` with named keys (matching the pattern already used by `ClearNightAnimation` stars), (2) ray state changes from cartesian `(x, y, speed)` to polar `(angle, dist, speed)`, and (3) sun body changes from a full 3px-radius circle at (48,4) to a clipped 7px-radius semicircle at (48,0).

**Major components:**
1. **`SunAnimation._draw_sun_body()`** — Changed: full ellipse at (48,4) r=3 replaced with ellipse at (48,0) r=7; Pillow auto-clips the top half producing a clean semicircle; glow ring preserved at r+2
2. **`SunAnimation._draw_ray()`** — Changed: cartesian diagonal advance replaced with polar outward travel; alpha computed from `dist / max_dist` ratio; `round()` not `int()` for pixel coordinates
3. **`SunAnimation._spawn_far()` / `_spawn_near()`** — Changed: random position across zone replaced with angle+distance at sun origin; initial stagger limited to 70% of MAX_DIST
4. **`tests/test_weather_anim.py::TestSunBody`** — Changed: pixel coordinate assertions updated for new geometry; new clustering assertion added

### Critical Pitfalls

1. **Far ray invisible fade tail** — Linear alpha fade drops below LED visibility threshold (~RGB 15,15,15) before reaching MAX_DIST. Use `MAX_DIST = 22` instead of 28, or a non-linear fade curve `(1 - dist/MAX_DIST) ** 0.6`, or a minimum alpha floor of 20. Validate on physical hardware — monitor rendering hides this problem.

2. **`int()` truncation creates directional bias** — `int()` truncates toward zero, systematically shifting all ray pixel positions left/up by up to 1 pixel when rays originate from a fixed point and fan outward. Use `round()` for all polar-to-pixel conversions. The existing codebase uses `int()` and the random-spawn design masked this bias. On the new radial system, the bias is amplified because all rays share the same origin.

3. **Pillow `ImageDraw` overwrites, does not alpha-blend** — Drawing 14 overlapping rays at the sun origin does NOT produce cumulative glow; each `draw.line()` overwrites previous pixels. Draw the sun body first (establishes bright center), then draw rays on top. Accept that the last ray drawn at any pixel wins; the sun body glow covers the origin overlap zone.

4. **Asymmetric ray fan from right-side sun position** — Sun at x=48 gives rightward rays only 16px of travel vs 48px for leftward rays. Narrow angle range to 0.15pi–0.85pi to avoid near-horizontal rightward rays that exit in 2-3 pixels and create flickering.

5. **Staggered spawn invisible zone** — Rays initialized at `random.uniform(0, MAX_DIST)` may start in the invisible tail of the fade curve, appearing sparse for the first 2-3 ticks. Cap stagger at 70% of MAX_DIST and raise the alpha draw threshold from 5 to 20 (matching the LED visibility floor).

## Implications for Roadmap

Based on research, the natural phase structure follows the dependency chain: the sun body establishes the origin point, the ray system depends on that origin, and tuning can only happen once the system works.

### Phase 1: Sun Body Geometry

**Rationale:** The half-sun at (48, 0) is the visual anchor for the entire overhaul. All ray spawn logic references `_SUN_X`, `_SUN_Y`, `_SUN_RADIUS`. Establishing these constants and the `_draw_sun_body()` implementation first removes ambiguity for Phase 2. This is also the smallest, most isolated change — good to get right before the more complex ray system.

**Delivers:** Visible half-sun semicircle at top-right of weather zone; two-layer glow (outer r+2 dim, inner r bright); sun body test assertions updated and passing.

**Addresses:** "Half-sun body at top edge" table stake; glow differentiator; Pitfall 5 (semicircle clipping fragility — add comment explaining the auto-clip dependency and test guard asserting no pixels above y=2).

**Avoids:** Drawing the sun body as a full circle (Pitfall 5), or placing it at y=4 where the full circle is visible (the original bug).

**Files:** `src/display/weather_anim.py` (constants + `_draw_sun_body`), `tests/test_weather_anim.py` (TestSunBody assertions).

### Phase 2: Radial Ray System

**Rationale:** The core bug fix. Depends on Phase 1 for the sun center position. This is the highest-complexity phase and where all identified critical pitfalls concentrate. Must address `round()` vs `int()`, alpha fade curve, angle range, and stagger range together — they interact.

**Delivers:** Rays emitting radially from the sun body; distance-based alpha fade; continuous respawn at sun origin; staggered initial distances; far/near depth layers preserved; all tests passing including new clustering assertion.

**Uses:** `math.cos()`, `math.sin()`, `math.radians()` from stdlib; Pillow `draw.line()` with RGBA fills; dict-based ray state structure matching `ClearNightAnimation` pattern.

**Implements:** Polar-to-cartesian particle system; distance-based alpha fade; respawn-at-origin loop; two-depth-layer assignment.

**Avoids:** Pitfall 1 (invisible fade tail — use reduced MAX_DIST or non-linear curve), Pitfall 2 (`int()` bias — use `round()`), Pitfall 3 (Pillow overwrite — draw order: body first, rays second), Pitfall 4 (asymmetric fan — angle range 0.15pi–0.85pi), Pitfall 6 (stagger invisible zone — cap stagger at 70% MAX_DIST).

**Files:** `src/display/weather_anim.py` (full `SunAnimation` rewrite), `tests/test_weather_anim.py` (ray-related assertions).

### Phase 3: Hardware Validation and Tuning

**Rationale:** Cannot verify LED visibility, perceptual ray brightness, diagonal ray dimness (Pitfall 7), or text readability from automated tests alone. PNG output on an LCD monitor shows sub-threshold RGB values that are completely dark on LED hardware. Hardware testing is the final quality gate.

**Delivers:** Confirmed LED visibility of sun body and rays at 2+ meter viewing distance; tuned alpha ranges, ray counts, and speed values if needed; "looks done but isn't" checklist cleared.

**Addresses:** Pitfall 7 (diagonal ray dimness — may require alpha boost for 30-60 and 120-150 degree rays), alpha range validation against actual LED hardware thresholds.

**Verification method:** `TEST_WEATHER=sun python src/main.py --simulated --save-frame` for before/after PNG comparison; physical Pixoo 64 testing with live animation.

**Files:** `src/display/weather_anim.py` (parameter value tuning only, no structural changes).

### Phase Ordering Rationale

- Phase 1 before Phase 2 because ray spawn coordinates reference `_SUN_X`, `_SUN_Y`, `_SUN_RADIUS` — finalizing the body first avoids rework on the ray system
- Phase 2 before Phase 3 because hardware tuning requires a working radial system to tune
- All three phases modify the same two files, eliminating cross-file coordination overhead
- Test-first approach within each phase: write failing assertions, implement, confirm green

### Research Flags

Phases with well-documented patterns (skip additional research-phase):
- **Phase 1 (Sun Body):** Pillow `ellipse()` auto-clipping behavior is well-documented and verified against installed Pillow 12.1.1. No unknowns.
- **Phase 2 (Radial Rays):** Polar-to-cartesian math is standard trigonometry. All pitfalls identified with concrete prevention strategies. No API unknowns.

Phases that may need targeted investigation during implementation:
- **Phase 3 (Hardware Tuning):** LED perceptual brightness is empirical. The alpha ranges (100-140 far, 160-220 near) are validated from v1.0, but the new fade curve changes effective RGB at various distances. Actual tuning values must be validated on the Pixoo 64 before the milestone is declared complete — this cannot be automated.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against installed Pillow 12.1.1 with working code proofs; math stdlib is stdlib. Zero uncertainty. |
| Features | HIGH | Derived directly from codebase analysis, existing test contracts, and original bug report. Feature list is constrained by the animation's closed interface. |
| Architecture | HIGH | Full codebase audit completed. Integration points precisely identified. Exact lines of code that change are enumerated. |
| Pitfalls | HIGH | Derived from numerical simulation, Pillow documentation, project debug history — not speculation. Recovery steps confirmed as 1-2 line fixes each. |

**Overall confidence:** HIGH

### Gaps to Address

- **Precise alpha/MAX_DIST tuning values**: The fade curve formula and MAX_DIST value (22 vs 28) should be finalized during Phase 2 implementation based on computed effective-RGB at max distance. The formula `alpha = base_alpha * (1 - dist/MAX_DIST) ** 0.6` is a starting recommendation but the exponent (0.6) needs hardware validation. This is an expected tuning gap, not a research gap.

- **Diagonal ray visibility on Pixoo 64**: Pitfall 7 (Bresenham diagonal dimness) is a known physical effect but whether it matters at the proposed alpha ranges (100-220) on this specific LED hardware cannot be determined without physical testing. Low probability given the high base alpha values, but flag for Phase 3 hardware check.

- **`test_sun_alpha_above_minimum` compatibility**: The existing test asserts `max_alpha >= 100`. With distance-based fade, the "max alpha" in any given frame depends on how many rays are near the sun. Verify this test still passes with the new system, or update the assertion to test peak alpha at spawn rather than max across all pixels in a frame.

## Sources

### Primary (HIGH confidence)
- `src/display/weather_anim.py` lines 276-368 — current `SunAnimation` class, exact code under modification
- `tests/test_weather_anim.py` TestSunBody, TestAnimationVisibility, TestColorIdentity — test contracts and alpha thresholds
- `src/display/renderer.py` `render_weather_zone()` — compositing pipeline, confirms `(bg, fg)` contract
- `src/display/layout.py` WEATHER_ZONE — 64x24 at y=40, zone dimensions
- `src/main.py` main loop — 1 FPS animation tick
- `.planning/debug/resolved/weather-animation-too-subtle.md` — LED visibility thresholds (RGB 15,15,15 floor)
- `.planning/debug/resolved/sunrays-showing-at-night.md` — day/night animation swap contract
- `.planning/todos/done/2026-02-22-sun-rays-animation-unrecognizable-without-sun-in-weather-zone.md` — original user bug report
- `docs/plans/2026-02-23-sun-ray-overhaul-design.md` — half-sun geometry, polar ray model specification
- `docs/plans/2026-02-23-sun-ray-overhaul.md` — task ordering, test-first approach, specific code changes
- Local benchmarks (this session): 0.02ms/tick for 14 rays at 15px on Python 3.14

### Secondary (MEDIUM confidence)
- [Pillow ImageDraw docs](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) — `pieslice()`, `point()`, `line()` signatures and auto-clipping behavior
- [Pillow GitHub issue #2496](https://github.com/python-pillow/Pillow/issues/2496) — RGBA draw overwrites pixels, does not alpha-blend
- [Bresenham's line algorithm](https://en.wikipedia.org/wiki/Bresenham's_line_algorithm) — diagonal pixel density and perceptual dimness
- [God Rays shader breakdown](https://www.cyanilux.com/tutorials/god-rays-shader-breakdown/) — distance attenuation, radial emission from point source
- [FastLED pixel reference](https://github.com/FastLED/FastLED/wiki/Pixel-reference) — LED gamma correction and minimum brightness thresholds

### Tertiary (MEDIUM-LOW confidence)
- [LED Matrix pixel art tutorial](https://learn.adafruit.com/pixel-art-matrix-display/overview) — 64x32 bitmap animation patterns; applicable by analogy to 64x24 zone
- [Pixel art tutorial (generalistprogrammer.com)](https://generalistprogrammer.com/tutorials/pixel-art-complete-tutorial-beginner-to-pro) — 1-2 pixel per frame motion guidance for LED displays

---
*Research completed: 2026-02-23*
*Ready for roadmap: yes*
