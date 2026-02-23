# Pitfalls Research

**Domain:** v1.2 Sun Ray Overhaul -- radial ray emission from half-sun body on 64x24 LED pixel display
**Researched:** 2026-02-23
**Confidence:** HIGH (pitfalls derived from codebase inspection, numerical simulation, Pillow documentation, and project debug history)

## Critical Pitfalls

### Pitfall 1: Far Rays Fade to Invisible Before Reaching MAX_DIST

**What goes wrong:**
The proposed linear alpha fade `alpha = base_alpha * (1.0 - dist / MAX_DIST)` causes far rays (base alpha 100-140) to drop below LED visibility threshold well before reaching MAX_DIST=28. Numerical simulation shows far rays become invisible (RGB channels below 15) at distance ~22, wasting the last 6 pixels of travel. This means far rays appear ~20% shorter than intended, and there is a dead zone around the edges of the weather zone where rays vanish into nothing instead of fading gracefully.

**Why it happens:**
The LED minimum brightness threshold (~RGB 15,15,15) creates a hard visibility floor. A linear fade looks mathematically smooth but on LED hardware, the bottom 20% of the fade range is completely invisible. The compositing step `alpha_composite(zone_region, layer)` in `renderer.py:124` further dilutes low-alpha pixels against the black background, pushing the effective visibility cutoff even higher.

**How to avoid:**
- Use a non-linear fade curve that spends more of its range in the visible brightness zone. A square-root fade `fade = max(0, 1.0 - (dist / MAX_DIST) ** 0.6)` keeps rays brighter longer and drops off sharply at the end, matching LED perceptual behavior better.
- Alternatively, reduce MAX_DIST from 28 to ~22 so rays respawn before they become invisible ghosts. This avoids the "ray exists but cannot be seen" problem entirely.
- Add a minimum alpha floor: `alpha = max(min_visible, int(base_alpha * fade))` where `min_visible` is around 20-25 for far rays, so rays either exist visibly or do not exist at all.
- Validate with the existing test `test_sun_alpha_above_minimum` which asserts `max_a >= 100`. This test only checks peak alpha, not fade-end visibility. Add a test that verifies rays at maximum travel distance are either invisible (alpha 0) or above the LED threshold -- no ghost zone.

**Warning signs:**
- Rays appear to stop short of the zone edges, creating a visible "halo boundary" instead of rays that reach across the weather zone.
- The weather zone has a ring of black pixels around the sun that rays never penetrate despite the fan spanning 180 degrees.
- On the physical Pixoo 64, rays look shorter than they do in PNG test renders (LCD screens can show RGB values that LEDs cannot).

**Phase to address:**
Ray implementation phase. The fade curve should be decided during implementation, not deferred to polish. Test on hardware early.

---

### Pitfall 2: int() Truncation Creates Systematic Directional Bias in Ray Positions

**What goes wrong:**
The proposed implementation converts polar-to-cartesian coordinates using `int(x)` and `int(y)`, which truncates toward zero. For a sun at position (48, 0), this creates a systematic bias: rays aimed rightward (positive x) are shifted left by up to 1 pixel, and rays aimed downward (positive y) are shifted up by up to 1 pixel. Simulation shows ~40% of ray endpoint positions differ between `int()` and `round()`, creating a visible leftward/upward skew in the ray pattern.

**Why it happens:**
Python's `int()` truncates (drops the decimal), while `round()` rounds to nearest integer. For `cos(angle) * distance = 48.71`, `int()` gives 48 but `round()` gives 49 -- a full pixel difference on a 64-pixel-wide display. On a large screen this is imperceptible, but on a 64x24 LED grid, 1 pixel is 1.5% of the display width. The cumulative effect across 14 rays is a visible asymmetric skew where rays aimed toward the right edge appear bunched together and rays aimed left spread out more naturally.

**How to avoid:**
- Use `round()` instead of `int()` for converting float polar coordinates to integer pixel positions. This centers the rounding error instead of biasing it directionally.
- Apply `round()` to both the start point `(x1, y1)` and end point `(x2, y2)` of each ray line.
- The existing codebase uses `int()` for the current SunAnimation (line 320-321 of `weather_anim.py`), but the current implementation does not use polar coordinates -- the bias exists but is masked by the random spawning. The new radial design amplifies the bias because all rays originate from the same point and fan outward.

**Warning signs:**
- The ray fan appears to lean slightly left when it should be symmetric.
- Rays aimed toward the right edge (small angles near 0) consistently appear 1 pixel shorter than equivalent rays aimed left (angles near pi).
- At angle pi/4 (45 degrees), the ray visually steps in a staircase pattern rather than a smooth diagonal.

**Phase to address:**
Ray implementation phase. A one-word fix (`round` instead of `int`), but must be deliberate.

---

### Pitfall 3: Overlapping Rays at Sun Origin Create Bright Hotspot (Pillow Draw Overwrites, Does Not Blend)

**What goes wrong:**
All 14 rays (9 far + 5 near) originate from the same sun center (48, 0). On each tick, rays at small distances have overlapping pixels near the origin. The natural assumption is that overlapping semi-transparent rays blend together, creating a smooth bright center that dims outward. **This does not happen.** Pillow's `ImageDraw.line()` on RGBA images **overwrites** pixels rather than alpha-blending them. The last ray drawn at a given pixel wins completely, replacing any previous ray's color/alpha. The result is that the sun center has flickering, inconsistent brightness as different rays overwrite each other frame-to-frame.

**Why it happens:**
Pillow's ImageDraw documentation explicitly states: "the image's pixel values are simply replaced by the new color" when drawing on RGBA images. There is no automatic alpha blending during draw operations -- only during `Image.alpha_composite()`. This means drawing 5 overlapping rays at alpha 160 at the sun center does NOT produce a bright cumulative glow. Instead, each ray overwrites the previous one, and the final brightness depends on which ray was drawn last (random order from the list).

This is confirmed by Pillow's own documentation and the GitHub issue tracker (python-pillow/Pillow#2496). The workaround requires drawing each element on a separate RGBA layer and compositing them together.

**How to avoid:**
- Accept the overwrite behavior for rays since they are thin lines (1px wide) and the overlap zone is small (only the first 2-3 pixels from the sun center). At those distances, the alpha is at maximum (no fade applied), so the overwrite produces the correct maximum brightness regardless of draw order.
- Do NOT attempt to draw a separate "glow" effect by drawing multiple overlapping shapes at the origin -- each new shape will replace the previous one, not add to it. The sun body ellipse (drawn separately before rays) handles the glow correctly because it is drawn as a single shape.
- If brighter cumulative glow is desired at the center, draw rays on individual RGBA layers and composite them together. However, this is expensive (14 separate Image objects per tick) and unnecessary given the sun body already provides the bright center.
- The existing `_draw_sun_body()` method draws the glow ellipse before rays are drawn, so rays will overwrite parts of the glow at the origin. Draw order matters: sun body first, then rays. The outer glow pixels that fall outside the ray lines remain visible.

**Warning signs:**
- Sun center appears to flicker slightly between frames (different ray overwrites each tick due to varying distances).
- Adding more rays at the center does not make the center brighter (the assumption that more overlapping = brighter is wrong with Pillow's draw model).
- The area immediately around the sun origin is dimmer than expected despite many rays passing through it.

**Phase to address:**
Ray implementation phase. Understand this behavior before writing ray drawing code. The proposed plan's draw order (sun body, then rays) is correct and should be preserved.

---

### Pitfall 4: Rightward Rays Exit the 64-pixel Zone Quickly, Creating Asymmetric Fan

**What goes wrong:**
The sun is positioned at x=48 in a 64-wide zone. Rays aimed rightward (angles 0 to ~45 degrees) only have 16 pixels of horizontal space before hitting the right edge (x=63). Rays aimed leftward (angles 135 to 180 degrees) have 48 pixels of horizontal space. Simulation shows rightward rays at angles below 25 degrees become invisible after only distance 16-17 (57% of MAX_DIST), while leftward rays travel the full distance. The visual result is a lopsided fan: full-length rays to the left but stubby rays to the right.

**Why it happens:**
The sun position was chosen to be top-right of the weather zone (x=48) to stay clear of left-side text (temperature, high/low, rain indicator all render starting at TEXT_X=2). This is the correct design choice for text readability, but it means the ray fan has dramatically different travel distances depending on direction. At angle 0.05*pi (9 degrees, nearly horizontal right), max visible distance is only 16 pixels. At angle 0.95*pi (171 degrees, nearly horizontal left), max visible distance is 28 pixels.

**How to avoid:**
- Accept the asymmetry as a feature, not a bug. In real life, a sun in the top-right corner WOULD produce longer rays to the left/below than to the right. The visual reads correctly as "sun in the corner, rays radiating outward."
- Bias the random angle distribution toward the center-left range (angles 0.3*pi to 0.8*pi) where rays have the most visible travel distance. Use fewer rays in the near-horizontal directions where they exit quickly.
- Consider limiting the angle range to 0.15*pi to 0.85*pi (27 to 153 degrees) to avoid nearly-horizontal rays that exit in 2-3 pixels and are perceived as flickers rather than rays.
- For rightward rays that DO exist, compensate by giving them slightly higher base alpha so they are brighter during their short visible life. This prevents the perception that the right side of the sun is "dead."

**Warning signs:**
- The sun appears to only shine leftward/downward, with the right side looking dark or inactive.
- Short-lived rightward rays create a flickering effect (they respawn rapidly because they exit bounds quickly, causing more respawn churn on the right than the left).
- The right side of the weather zone (x=48-63) has no visible ray activity despite the sun being positioned there.

**Phase to address:**
Ray implementation phase. The angle range in `_random_angle()` should be tuned during implementation. The proposed 0.05*pi to 0.95*pi range includes nearly-horizontal rays that contribute flickering without visual payoff.

---

### Pitfall 5: Half-Sun Semicircle Clipping Depends on Pillow Auto-Clipping Behavior

**What goes wrong:**
The design places the sun center at y=0 with radius 7, relying on Pillow's auto-clipping to naturally hide the top half of the ellipse (y < 0 is outside the image). This works correctly -- Pillow documents that "any pixels drawn outside of the image bounds will be discarded." However, the ellipse bounding box `[sx-r, sy-r, sx+r, sy+r]` becomes `[41, -7, 55, 7]`. If a future refactor changes the animation to render on a larger canvas and then crop, or if the weather zone offset calculation changes, the "free clipping" breaks and a full circle appears instead of a semicircle.

**Why it happens:**
Auto-clipping is an implicit behavior, not an explicit design choice. The code does not contain a comment saying "we rely on clipping at y=0 for the semicircle effect." A future developer (or AI) refactoring the animation system might add a margin, change the canvas size, or render at a different offset, breaking the implicit contract.

**How to avoid:**
- Add a clear comment in `_draw_sun_body()` explaining that the semicircle effect depends on the sun center being at y=0 and the image bounds clipping the top half.
- Add a test that verifies no sun body pixels exist above y=2 (allowing for the visible lower hemisphere but confirming the top hemisphere is clipped). This makes the semicircle behavior explicit and test-guarded.
- Consider using `ImageDraw.pieslice()` to draw an explicit semicircle instead of relying on auto-clipping. This is more robust but produces slightly different visuals (hard edge vs. smooth clipping). For a 7-pixel radius on LED hardware, the difference is negligible.

**Warning signs:**
- After a refactor, the sun appears as a full circle instead of a half-sun at the top edge.
- The sun body test (`test_sun_body_produces_warm_pixels_at_position`) passes but the visual is wrong because the test only checks pixels below the center.
- Changing `_SUN_Y` from 0 to any other value produces a visible full circle (the clipping only works at y=0).

**Phase to address:**
Sun body implementation phase. Add the explanatory comment and a clipping assertion test alongside the body drawing code.

---

### Pitfall 6: Staggered Initial Distances Bypass Quality Gate on First Tick

**What goes wrong:**
The proposed design staggers initial ray distances using `random.uniform(0, MAX_DIST)` so the animation starts as a continuous effect rather than a burst from the center. This is a good UX decision. However, rays spawned at large initial distances (e.g., distance 25) will have very low alpha on the first tick and may immediately trigger a respawn on the second tick. The first few ticks will have a burst of respawning as these high-distance rays recycle, creating a brief visual stutter at animation startup.

**Why it happens:**
The fade formula `alpha = base_alpha * (1.0 - dist / MAX_DIST)` means a ray starting at distance 25 with base alpha 120 has effective alpha of only 12 -- below LED visibility. It draws an invisible pixel and then on the next tick moves to distance 25.6, where it is still invisible. It may take 2-3 ticks to reach MAX_DIST and respawn. Meanwhile, 3-4 rays started at high distances are all invisible simultaneously, reducing the visible ray count from 14 to ~10 during startup.

Additionally, the alpha check threshold in `_draw_ray()` is `alpha > 5` (from the proposed plan). Rays with alpha 6-15 pass this check and get drawn, but produce RGB values below the LED visibility threshold. They waste draw calls on invisible pixels.

**How to avoid:**
- Limit initial stagger range to `random.uniform(0, MAX_DIST * 0.7)` so no ray starts in the invisible tail of the fade curve.
- Raise the alpha draw threshold from `alpha > 5` to `alpha > 20` to match the LED visibility floor. Rays below this threshold should be immediately recycled rather than drawn invisibly.
- Alternatively, cap the stagger at the distance where alpha equals the LED visibility threshold: `max_stagger = MAX_DIST * (1.0 - LED_THRESHOLD / base_alpha)`.
- The first-tick test `test_rays_cluster_near_sun` from the proposed plan checks that 30% of pixels are near the sun. This threshold may be too low to catch the invisible-ray problem since invisible rays contribute zero pixels to either bucket.

**Warning signs:**
- The animation looks sparse for the first 2-3 seconds, then fills in as high-distance rays respawn at the center.
- Debug output shows rays being drawn at alpha values 5-15 (below LED visibility) on every tick.
- The `test_sun_animation_still_has_rays` test occasionally fails non-deterministically because random stagger places too many rays in the invisible zone.

**Phase to address:**
Ray implementation phase. The stagger range and alpha threshold should be tuned together.

---

### Pitfall 7: Diagonal Rays Appear Dimmer Than Vertical/Horizontal Due to Bresenham Pixel Density

**What goes wrong:**
Pillow's `ImageDraw.line()` uses Bresenham's algorithm for rasterizing lines. A 1-pixel-wide diagonal line illuminates fewer pixels per unit length than a horizontal or vertical line. A ray at 45 degrees traveling 10 pixels of distance illuminates ~10 pixels, while a horizontal ray traveling 10 pixels illuminates ~10 pixels. But the diagonal ray covers a longer physical distance (10*sqrt(2) = 14.1 pixels diagonally) with the same number of lit pixels, making it appear ~30% dimmer to the human eye. On LED hardware with minimum brightness thresholds, this can push diagonal rays below visibility while axis-aligned rays remain visible.

**Why it happens:**
Bresenham's line algorithm produces 1 pixel per step along the major axis. For a 45-degree line, there is one pixel per column AND one per row, so no doubling. For a near-horizontal line, there might be 2-3 pixels in consecutive columns at the same row, creating a denser appearance. This is a fundamental property of rasterized line drawing, not a Pillow bug.

**How to avoid:**
- Accept this as a characteristic of low-resolution pixel art. At 64x24 pixels, anti-aliasing is not practical, and the brightness variation is part of the aesthetic.
- If diagonal ray dimness becomes problematic on hardware, compensate by giving diagonal-angle rays slightly higher base alpha (e.g., +20 for angles between 30-60 and 120-150 degrees).
- Use 2-pixel-wide rays for the near (fg) layer to increase pixel density. Pillow's `draw.line(..., width=2)` doubles the pixels, which helps diagonal visibility. However, on a 64x24 grid, 2-pixel-wide rays may be too thick.
- For far rays (bg layer), this is less of a concern because they are already dim and meant to be subtle background texture.

**Warning signs:**
- Rays aimed at ~45 degrees look noticeably dimmer or thinner than rays aimed straight down (90 degrees).
- On the physical LED display, some ray angles appear missing despite being drawn at the same alpha as visible rays.
- The `_sample_particle_rgb` test helper counts total colored pixels -- diagonal rays contribute fewer pixels per ray, potentially causing the "rays should still be active" test to fail if the threshold assumes uniform pixel density.

**Phase to address:**
Hardware testing phase. This is unlikely to be a problem at the proposed alpha ranges (100-220), but should be validated on the Pixoo 64.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `int()` for float-to-pixel conversion | Simpler, fewer function calls | Systematic directional bias in ray rendering | Never for radial geometry from a fixed origin -- use `round()` |
| Relying on image bounds for semicircle clipping | No extra code needed, Pillow handles it | Fragile if canvas size or offset changes | Acceptable now with comment + test guard. Replace with explicit `pieslice()` if refactored later |
| Linear fade curve for alpha | Simple formula, easy to understand | Last 20% of ray travel is invisible on LED hardware | Acceptable for initial implementation if MAX_DIST is reduced to compensate. Replace with non-linear fade if visual quality is insufficient on hardware |
| Hardcoded angle range 0.05pi to 0.95pi | Full semicircle coverage | Nearly-horizontal rays exit bounds quickly, creating flicker | Acceptable for initial implementation but should be narrowed to 0.15pi-0.85pi if right-side flicker is observed |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Polar-to-pixel conversion | Using `int()` which truncates toward zero, creating directional bias | Use `round()` for symmetric rounding. Both start and end coordinates of each ray line must be rounded consistently |
| Pillow ImageDraw on RGBA | Assuming overlapping semi-transparent draws blend together | They overwrite. Each `draw.line()` replaces previous pixel values. Draw order matters. Use separate layers + `alpha_composite()` only if cumulative blending is needed |
| Sun body + ray compositing order | Drawing rays before the sun body, letting the body overwrite ray origins | Draw sun body first, then rays on top. The body provides the bright center, rays extend outward from it |
| Alpha fade + LED visibility | Testing alpha fade visually on a monitor (where RGB 5,5,5 is visible) | LED pixels below ~RGB(15,15,15) are completely dark. Test on hardware or use the computed effective-RGB threshold |
| Existing test suite compatibility | Breaking `test_sun_particles_are_yellow_dominant` by changing ray colors | The existing test checks R > B+50 and G > B+30 for sun particles. New ray colors must maintain yellow dominance. The proposed colors (240,200,40) and (255,240,60) are correct |
| WindEffect compatibility | Assuming WindEffect works with polar ray coordinates | WindEffect modifies `far_drops`, `near_drops`, `far_flakes`, `near_flakes` attributes by name. The new `far_rays`/`near_rays` use different storage format (angle, dist, speed, length, alpha) not (x, y). WindEffect will silently skip SunAnimation -- which is correct since sun should not have wind drift. But verify it does not crash |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Trigonometric calculations per ray per tick | Unnoticeable at 14 rays/tick | `math.cos()` and `math.sin()` are C-implemented and fast. 14 calls per tick is negligible | Never -- this is not a concern at 1 FPS with 14 rays |
| Drawing rays that are entirely outside bounds | Wasted draw calls that produce no visible pixels | Check if ray start AND end are both outside bounds before calling `draw.line()`. The proposed plan's bounds check is correct but could be tightened | Never significant -- Pillow's auto-clipping handles this efficiently |
| Respawn churn for short-lived rightward rays | Rays at angles < 20deg exit bounds after 2-3 ticks and respawn repeatedly, burning CPU on spawn+draw+recycle | Limit angle range to avoid near-horizontal rightward rays, or bias angle distribution | Not a real performance issue at 14 rays, but creates visual flicker |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Rays appear to originate from empty space (not the sun body) | User sees streaks but no connection to "sunshine" -- same problem as v1.0 | Ensure rays start at distance 0 (sun center) and the sun body is drawn behind them. The bright origin point sells the "radiating from sun" effect |
| Asymmetric ray fan looks broken rather than natural | User thinks the right side of the animation is not working | Make the asymmetry deliberate: more rays aimed left/down where they have room. Fewer but brighter rays aimed right |
| Rays too sparse at 1 FPS (14 thin lines on 1536 pixels) | User sees occasional flickers rather than "sunshine" | Ensure rays are at least 3-4 pixels long even at short distances. The proposed length range (2-4 far, 4-7 near) is adequate. If still too sparse, add 2-3 more far rays |
| Ray animation looks identical to the old scattered rays | The overhaul fails its primary goal of being recognizable as sunshine | The key visual difference is origin point: ALL rays must clearly emanate from the sun body position, not from random locations. This is the make-or-break test |
| Half-sun glow obscures temperature text on sunny days | Sun glow at x=48 extends left toward text at x=2 | The glow radius (+2px) means glow reaches x=39 at most. Temperature text starts at x=2. No overlap. But verify on hardware that the glow does not create ambient brightness that washes out text in the weather zone |

## "Looks Done But Isn't" Checklist

- [ ] **Ray origin:** All rays visually appear to come from the sun body position on the physical LED display, not from random locations in the zone
- [ ] **Half-sun:** Only the bottom hemisphere of the sun is visible. No full circle appears at the top of the weather zone
- [ ] **Alpha fade:** Rays fade smoothly to nothing with distance. No abrupt cutoff, no ghost rays (drawn but invisible)
- [ ] **Text readability:** Temperature text (yellow, x=2), high/low (teal, x=2), and rain text (white, x=2) are all still readable during sun animation
- [ ] **Layer depth:** Far rays pass behind text (bg layer), near rays pass in front of text (fg layer). Text should be sandwiched between the two
- [ ] **Color identity:** Existing `test_sun_particles_are_yellow_dominant` test passes -- rays are still warm yellow
- [ ] **Night transition:** Sun animation swaps to ClearNightAnimation when `is_night` changes. No sun rays at night (regression from resolved bug)
- [ ] **Reset:** `anim.reset()` produces a fresh set of staggered rays, not a burst from center
- [ ] **Respawn:** Rays that exit bounds or fade out respawn at the sun center with new random angles, producing continuous animation
- [ ] **Angle coverage:** Rays spread across the full downward semicircle, not clustered in one direction
- [ ] **1 FPS motion:** At the 1-second interval between pushes, ray movement is perceptible. Rays should move 2-4 pixels per tick (matching their speed values) for visible motion at 1 FPS

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Rays invisible on LED hardware (alpha too low after fade) | LOW | Increase base alpha ranges or reduce MAX_DIST. All changes are numeric constants in SunAnimation class |
| int() truncation bias visible | LOW | Replace `int()` with `round()` in `_draw_ray()`. Two lines changed |
| Asymmetric fan looks broken | LOW | Narrow angle range in `_random_angle()`. One line changed |
| Semicircle clipping breaks after refactor | MEDIUM | Switch from auto-clipping to explicit `pieslice()`. Requires rewriting `_draw_sun_body()` and updating tests |
| Overlapping ray overwrite creates flicker at origin | LOW | Draw sun body last instead of first (body overwrites ray origins, hiding the flicker). Or accept it since the sun body glow covers the overlap zone |
| First-tick stutter from staggered invisible rays | LOW | Reduce stagger range from `(0, MAX_DIST)` to `(0, MAX_DIST * 0.7)`. One constant changed |
| All rays look the same -- overhaul fails its purpose | MEDIUM | The entire point is rays emanating from the sun body. If this does not read as "sunshine" on the LED display, the approach may need more fundamental changes (e.g., adding a warm gradient background, widening rays, or using a different visual metaphor) |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Far ray invisible fade tail | Ray implementation | Compute effective RGB at MAX_DIST; verify it exceeds LED threshold or ray is recycled before reaching that distance |
| int() truncation bias | Ray implementation | Use `round()` in polar-to-pixel conversion. Visual inspection of ray symmetry on hardware |
| Pillow draw overwrite (not blend) | Ray implementation | Understand behavior before coding. Accept for thin rays, draw sun body before rays |
| Asymmetric ray fan | Ray implementation + hardware testing | Tune angle range after viewing on physical display. Start with 0.15pi-0.85pi |
| Semicircle clipping fragility | Sun body implementation | Add comment explaining clipping dependency + test asserting no pixels above y=2 |
| Staggered spawn invisible zone | Ray implementation | Limit stagger to 70% of MAX_DIST. Raise alpha draw threshold to 20 |
| Diagonal ray dimness | Hardware testing | Validate on Pixoo 64 that diagonal rays are visible. Compensate with alpha boost if needed |

## Sources

- Codebase inspection: `src/display/weather_anim.py` (current SunAnimation, lines 276-368), `src/display/renderer.py` (_composite_layer, lines 122-126), `src/display/layout.py` (zone definitions, color constants) -- HIGH confidence
- Debug history: `.planning/debug/resolved/weather-animation-too-subtle.md` (LED visibility thresholds, double-alpha root cause) -- HIGH confidence
- Debug history: `.planning/debug/resolved/sunrays-showing-at-night.md` (day/night animation swap) -- HIGH confidence
- Proposed design: `docs/plans/2026-02-23-sun-ray-overhaul-design.md` and `docs/plans/2026-02-23-sun-ray-overhaul.md` -- HIGH confidence
- Numerical simulation: polar-to-pixel conversion, alpha fade calculations, zone boundary analysis (run in this research session) -- HIGH confidence
- [Pillow ImageDraw documentation](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) -- draw overwrite behavior, auto-clipping -- HIGH confidence
- [Pillow GitHub issue #2496](https://github.com/python-pillow/Pillow/issues/2496) -- RGBA draw does not alpha-blend -- HIGH confidence
- [Bresenham's line algorithm](https://en.wikipedia.org/wiki/Bresenham's_line_algorithm) -- diagonal line pixel density -- HIGH confidence
- [Alpha compositing in Pillow](https://jdhao.github.io/2022/04/01/image_alpha_composite_pillow/) -- compositing mechanics -- MEDIUM confidence
- [FastLED pixel reference](https://github.com/FastLED/FastLED/wiki/Pixel-reference) -- LED gamma correction and minimum brightness -- MEDIUM confidence

---
*Pitfalls research for: v1.2 Sun Ray Overhaul (radial ray emission from half-sun body)*
*Researched: 2026-02-23*
