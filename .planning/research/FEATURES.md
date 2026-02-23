# Feature Landscape

**Domain:** Radial sun ray animation overhaul for Pixoo 64 weather dashboard
**Researched:** 2026-02-23
**Milestone:** v1.2 Sun Ray Overhaul

## Table Stakes

Features that make the sun animation recognizable as sunshine on a 64x64 LED display. Missing = animation looks abstract/confusing (the exact problem that triggered this overhaul).

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Half-sun body at top edge of weather zone | Without a visible sun, rays look like random streaks. The original todo explicitly calls this out: "hard to understand that the sun rays are sun rays." A semicircle clipped at y=0 implies the sun is just above the horizon/zone boundary | Low | Draw full ellipse centered at (48, 0) with radius 7. Pillow naturally clips the top half beyond the image boundary, producing a 14px-wide, 7px-tall arc. Two-layer glow: dimmer outer (r+2) then bright inner body |
| Rays originate from sun center | Rays that spawn randomly across the 64x24 zone have no spatial relationship to the sun body. Radial emission from the sun position is what makes the visual read as "sunshine" vs "random yellow lines" | Med | Store rays in polar coordinates (angle, distance) relative to sun center (48, 0). Convert to cartesian for drawing. Angle range: 0.05pi to 0.95pi (downward-facing semicircle fan) |
| Rays fade with distance | Light attenuates. Without fade, rays look like solid lines flying away from the sun rather than beams of light. Distance-based alpha fade is the key visual cue that these are light beams, not particles | Low | Linear fade: `alpha = base_alpha * (1.0 - distance / MAX_DIST)`. Kill ray when alpha drops below ~5 (below LED visibility threshold). MAX_DIST of 28 covers most of the weather zone |
| Ray respawn at sun origin | Continuous animation requires rays to loop. When a ray fades out or exits the zone, it must reappear at the sun with a new random angle, maintaining the illusion of continuous light emission | Low | On respawn: reset distance to 0, assign new random angle in the downward fan, re-randomize speed and length. Initial rays staggered at varying distances so animation starts mid-flow, not as a burst |
| Two-depth-layer system preserved | The existing animation architecture composites bg (behind text) and fg (in front of text) for a 3D depth effect. Sun rays must continue to use this system. Far rays behind weather text, near rays over it | Low | Far rays: 9 count, slower (0.4-0.8 speed), shorter (2-4px), dimmer (alpha 100-140), color (240, 200, 40). Near rays: 5 count, faster (0.8-1.6 speed), longer (4-7px), brighter (alpha 160-220), color (255, 240, 60). These values match the existing palette exactly |
| Yellow color palette maintained | Sun = warm yellow is established across the dashboard (clock icon, weather icon, existing animation). Changing it would break the visual language | Low | No color changes needed. Far: (240, 200, 40), Near: (255, 240, 60), Body: (255, 220, 60) with (255, 200, 40) glow. All proven LED-visible at current alpha ranges |
| Tests pass for new geometry | ANIM-03 requirement. Existing tests assert sun body position, glow presence, ray activity, yellow color dominance, and alpha minimums. These must pass with new coordinates | Med | TestSunBody needs coordinate updates for (48, 0) and radius 7 vs old (48, 4) and radius 3. Glow check pixel coordinate changes. TestColorIdentity and TestAnimationVisibility should pass without changes since color/alpha ranges are preserved |

## Differentiators

Features that elevate the sun animation beyond "minimally recognizable." Not strictly required but make the visual effect polished.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Staggered initial ray distances | Without staggering, all rays start at distance 0 on animation init/reset, producing an ugly burst effect. Staggering makes the animation look like it was already running | Low | On spawn: `distance = random.uniform(0, MAX_DIST)` instead of 0. Already in the design plan. Minimal code, big visual impact |
| Ray length varies per ray | Fixed-length rays look mechanical. Variable length (2-4px far, 4-7px near) adds organic quality. The existing rain/snow animations use similar per-particle randomization | Low | Already specified in the ray spawn parameters. Each ray gets its own random length on spawn and respawn |
| Angle range avoids pure horizontal | Rays at exactly 0 or pi radians shoot perfectly horizontal, which looks unnatural. Constraining to 0.05pi-0.95pi keeps all rays in a visually pleasing downward fan | Low | `random.uniform(0.05 * math.pi, 0.95 * math.pi)` -- one line. Prevents edge-case visual artifacts where a ray hugs the top edge |
| Ray origin clustering test | A test that verifies rays cluster near the sun position rather than scattering randomly. This is the regression gate that prevents reintroduction of the original bug | Med | Count non-transparent pixels within radius 15 of sun vs outside. Assert at least 30% are near the sun on first tick. This is the "did we actually fix the core problem?" test |
| Smooth reset behavior | `reset()` method should re-stagger rays at varied distances, matching the init behavior. A reset that puts all rays at distance 0 creates a visible burst artifact whenever weather data refreshes | Low | `reset()` clears and re-calls `_spawn_far(9)` and `_spawn_near(5)`, which already include distance staggering. Consistent with all other animation reset methods |

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Dynamic ray count based on weather intensity | Sun animation does not receive precipitation_mm or any intensity parameter. Clear sky is clear sky -- there's no "intensity" gradient for sunshine. Adding unused parameters bloats the API | Keep fixed 9 far + 5 near rays. If variable sunshine intensity is ever needed (partly cloudy), it belongs in a future CompositeAnimation combining SunAnimation with CloudAnimation |
| Rotating sun body or pulsing glow | At 64x64 resolution with a 7px radius semicircle, rotation or pulsing would look like flickering artifacts, not animation. LED pixels have discrete brightness levels -- subtle glow pulsing gets quantized to visible jumps | Static sun body with static glow. The rays provide all the animation. The body is the anchor point |
| Curved/bent rays | Rays that curve as they travel would require bezier rendering per frame, adding complexity for a visual effect invisible at this resolution. At 64x64, a 4-7 pixel line segment has no room to curve meaningfully | Straight line segments from polar-to-cartesian math. Pillow's `draw.line()` is perfectly suited |
| Ray width variation (thick/thin rays) | Pillow's `draw.line()` width parameter on short line segments at this resolution produces blocky rectangles, not elegant beams. Width 1 is the correct choice at 64x64 | All rays width 1. Visual distinction between far/near comes from alpha and length, not width |
| Per-pixel dithering on ray bodies | Dithering techniques (checkerboard patterns for semi-transparency) are used in sprite-based pixel art where true alpha isn't available. The RGBA compositing pipeline already handles transparency correctly -- dithering would fight the alpha system | Use alpha channel for all transparency effects. The RGBA compositing pipeline (Image.alpha_composite) handles this natively |
| Wind effect on sun rays | WindEffect currently targets particle lists (far_drops, near_drops, far_flakes, near_flakes). Sun rays use polar coordinates (angle, distance), not cartesian positions. Wind would need to modify angles, which produces bizarre visual results (rays bending sideways) | Sun rays are not affected by wind. This matches reality: sunbeams don't blow sideways. If wind is strong enough to matter, the weather condition would be clouds/rain, not clear sky |
| Sunrise/sunset color transitions | Changing ray colors from warm-yellow to orange-red based on time of day adds complexity (time dependency in animation, color interpolation) for minimal visual payoff at this resolution | Fixed warm yellow palette. Time-of-day awareness already exists at the weather routing level (is_night selects ClearNightAnimation). If sunrise/sunset effects are ever desired, they belong in new animation classes |
| Sun body position varies with time | Moving the sun across the weather zone to simulate sun position adds an API dependency (time/azimuth), complicates the ray origin math, and the 64x24 zone is too small for the motion to be meaningful | Fixed position at (48, 0). Top-right of weather zone, clear of left-side weather text. Static anchor |

## Feature Dependencies

```
Sun Body (half-sun semicircle at y=0)
  |
  +--> Ray Origin (rays emit from sun position)
  |      |
  |      +--> Ray Fade (alpha decreases with distance from origin)
  |      |
  |      +--> Ray Respawn (loop back to origin when faded/exited)
  |      |
  |      +--> Staggered Init (rays start at varied distances)
  |
  +--> Depth Layers (far rays on bg, near rays on fg)
         |
         +--> Color Palette (preserved yellows on each layer)

Test Updates
  |
  +--> Sun Body Tests (new coordinates for TestSunBody)
  |
  +--> Ray Origin Test (new TestSunRayOrigin clustering assertion)
  |
  +--> Existing Tests (TestColorIdentity, TestAnimationVisibility should pass unchanged)

Note: All ray features depend on sun body position being finalized first.
The body position (48, 0) determines the polar coordinate origin for all rays.
```

## MVP Recommendation

The implementation plan in `docs/plans/2026-02-23-sun-ray-overhaul.md` already captures the correct task ordering. Summarized here:

### Prioritize (in order):

1. **Update sun body tests** -- Write failing tests for new half-sun geometry at (48, 0) with radius 7. Tests drive the implementation.
2. **Add ray origin clustering test** -- Write failing test that rays cluster near the sun. This is the regression gate for the core bug fix.
3. **Rewrite SunAnimation class** -- Replace cartesian random-position rays with polar radial-emission rays. New half-sun body. This is the single production code change.
4. **Full test suite verification** -- All 96+ tests must pass, confirming no regressions in other animations.

### Defer:

- **Visual hardware testing** -- Can only be done on the physical Pixoo 64. Not blockable in automated tests. Verify after deployment that the half-sun is visible and rays read as "sunshine" at 2+ meters viewing distance.
- **Alpha tuning** -- The current alpha ranges (100-140 far, 160-220 near) are empirically validated from v1.0. Start with these values. Only tune if physical hardware testing reveals visibility issues.

### Complexity Assessment:

This is a **low-risk, focused refactor** of a single animation class. The change is entirely within `SunAnimation` in `weather_anim.py`, touching no other animation classes, no rendering pipeline, no providers, and no layout code. The math (polar to cartesian, distance-based fade) is straightforward trigonometry. The main risk is coordinate/geometry bugs, which the test suite catches.

**Estimated scope:** ~90 lines of production code change (replace `SunAnimation`), ~40 lines of test changes. No new files, no new dependencies.

## Sources

- Codebase analysis: `src/display/weather_anim.py` lines 276-368 (existing SunAnimation), `src/display/layout.py` line 23 (WEATHER_ZONE: 64x24 at y=40) -- PRIMARY source for constraints and existing patterns (HIGH confidence)
- Codebase analysis: `tests/test_weather_anim.py` lines 603-632 (TestSunBody), lines 113-117 (sun alpha test), lines 220-231 (sun color test) -- existing test contracts (HIGH confidence)
- Design plan: `docs/plans/2026-02-23-sun-ray-overhaul-design.md` -- half-sun geometry, polar ray model, depth layers specification (HIGH confidence)
- Implementation plan: `docs/plans/2026-02-23-sun-ray-overhaul.md` -- task ordering, test-first approach, specific code changes (HIGH confidence)
- Original bug report: `.planning/todos/done/2026-02-22-sun-rays-animation-unrecognizable-without-sun-in-weather-zone.md` -- user feedback that sun rays are "hard to understand" without visible sun (HIGH confidence)
- [Sun Beams / God Rays Shader Breakdown](https://www.cyanilux.com/tutorials/god-rays-shader-breakdown/) -- distance-based attenuation, radial emission from point source, fade math applicable to 2D (MEDIUM confidence)
- [God Rays Part 1](https://blog.cclarke-magrab.me/blogs/graphics/god-rays-01) -- ray-casting from point source, sampling along ray path, directional scattering approximation (MEDIUM confidence)
- [Volumetric Lighting - Wikipedia](https://en.wikipedia.org/wiki/Volumetric_lighting) -- crepuscular rays theory, light scattering through medium (HIGH confidence)
- [Pixel Art Tutorial: Complete Guide](https://generalistprogrammer.com/tutorials/pixel-art-complete-tutorial-beginner-to-pro) -- 64x64 canvas guidance, 1-2 pixel movement per frame max for smooth animation, 4-16 color palette per sprite (MEDIUM confidence)
- [Semi-Transparency Dithering - Lospec](https://lospec.com/pixel-art-tutorials/semi-transparency-dither-by-st0ven) -- dithering as transparency substitute; confirms RGBA alpha compositing is the correct approach when true alpha is available (MEDIUM confidence)
- [LED Matrix Display for Pixel Art](https://learn.adafruit.com/pixel-art-matrix-display/overview) -- LED matrix fundamentals, 64x32 bitmap handling, animation sprite sheet patterns (MEDIUM confidence)
