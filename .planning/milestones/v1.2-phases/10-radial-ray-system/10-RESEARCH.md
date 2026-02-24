# Phase 10: Radial Ray System - Research

**Researched:** 2026-02-23
**Domain:** Polar-coordinate ray emission, distance-based alpha fade, 1 FPS LED animation on 64x24 weather zone
**Confidence:** HIGH

## Summary

Phase 10 replaces the current random-scatter diagonal sun rays with a polar radial ray system emitting outward from the corner-anchored sun body at `(63, 0)`. The core transformation is moving from cartesian random-position spawning to polar-coordinate rays defined by angle and distance from the sun center. Each ray travels outward along a fixed angle, fading in alpha as distance increases, and respawns at the origin when it either fades out or exits the zone. The animation uses the existing two-depth-layer system: 9 far rays on the bg layer (behind weather text) and 5 near rays on the fg layer (in front of text).

The mathematical foundation is straightforward Python `math.cos()`/`math.sin()` for polar-to-cartesian conversion. The useful angular range for the downward-facing fan from `(63, 0)` is approximately 95 to 160 degrees (where 90 = straight down and 180 = straight left). This range produces rays that cover the visible 64x24 zone without going upward or off the right edge. Rays beyond 160 degrees travel nearly horizontally along the top edge and have limited visual impact; rays below 95 degrees exit the right side of the zone too quickly. Maximum ray travel distances range from 24px (straight down at 90 degrees) to 49px (at 160 degrees toward the left edge).

The key design challenge is making 14 rays (9 far + 5 near) look like natural sunlight on a 64x24 LED matrix running at 1 FPS. The rays must start mid-flow (staggered initial distances) to avoid the "burst from origin" effect, fade smoothly with distance to create a light-emission look, and cycle continuously without visible gaps or stalls.

**Primary recommendation:** Replace the five ray state fields `[x, y, speed, length, alpha]` with polar fields `[angle, distance, speed, max_distance, base_alpha]`. Each tick advances `distance` by `speed`, converts to cartesian for drawing, and applies alpha fade proportional to `distance / max_distance`. When `distance >= max_distance` or the cartesian position exits the zone, reset `distance` to 0 (respawn at origin). Initialize with random distances (not all zero) for staggered mid-flow start.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation decisions are at Claude's discretion.

### Claude's Discretion
User deferred all visual tuning decisions to Claude, with feedback to come during UAT. The following areas are all open for Claude to decide:

**Fan spread & angle:**
- Exact angular range of the downward-facing fan from corner position
- Ray distribution across the fan (even vs jittered)
- Zone coverage (how far rays reach across the 64x24 weather zone)

**Ray visual style:**
- Ray thickness (1px vs 2px, uniform vs mixed by layer)
- Whether rays taper along their length
- Edge treatment (hard pixel lines vs soft glow halo)
- Length variation between individual rays

**Ray motion & speed:**
- Motion curve (constant, accelerating, or decelerating)
- Whether rays have angular drift as they travel outward
- Speed differentiation between near and far layers (parallax)
- Overall animation pacing (calm ambient vs active radiating)

**Fade & color tuning:**
- Whether color shifts along ray length or stays uniform warm yellow
- Fade curve shape (linear vs exponential vs custom)
- Alpha ranges for LED visibility on both layers
- How quickly rays cycle (linger time before respawn)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANIM-03 | Rays emit radially outward from sun center across a downward-facing fan | Polar-coordinate ray system: each ray has a fixed angle within the 95-160 degree fan, travels outward from (63, 0). Math verified: `x = cx + cos(angle) * distance`, `y = cy + sin(angle) * distance`. |
| ANIM-04 | Ray alpha fades with distance from sun | Alpha formula: `alpha = base_alpha * (1 - distance / max_distance)`. Linear fade from full brightness at origin to zero at max distance. LED visibility threshold (~15 alpha) means rays effectively disappear before max_distance -- natural fade-out. |
| ANIM-05 | Rays respawn at sun origin when faded or exited zone | When `distance >= max_distance` OR cartesian position exits 64x24 bounds, reset `distance = 0` (respawn at origin). Continuous cycle with no stall. |
| ANIM-06 | Far rays (9) on bg layer, near rays (5) on fg layer -- depth system preserved | Existing `SunAnimation.tick()` already draws `far_rays` on `bg_draw` and `near_rays` on `fg_draw`. The bg/fg compositing pipeline in `renderer.py::render_weather_zone()` handles depth ordering. Keep 9 far / 5 near split. |
| ANIM-07 | Staggered initial ray distances so animation starts mid-flow | On init, each ray's `distance` is `random.uniform(0, max_distance)` instead of 0. This distributes rays across their full travel path so no "burst from origin" occurs on first frame. |
| TEST-02 | Ray origin clustering test -- rays concentrate near sun, not randomly scattered | Test: after several ticks, sample ray positions and verify they cluster around (63, 0) significantly more than a random distribution. Can measure average distance-from-sun or verify rays within N pixels of sun center. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow (PIL) | 12.1.1 | RGBA image drawing, line rendering, alpha compositing | Already used for all display rendering. `ImageDraw.line()` and `ImageDraw.point()` for ray pixels. |
| Python math | stdlib | `cos()`, `sin()`, `radians()` for polar-to-cartesian conversion | Already imported in weather_anim.py. No new dependencies. |
| Python random | stdlib | Ray angle jitter, distance staggering, speed variation | Already imported in weather_anim.py. |

### Supporting
No additional libraries needed. All functionality is within Pillow and Python stdlib.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polar ray coordinates (angle + distance) | Cartesian ray path with pre-computed slopes | Polar is more natural for radial emission; cartesian would need per-ray dx/dy pre-computation. Polar is cleaner for fade-from-origin. |
| PIL `line()` for ray segments | PIL `point()` pixel-by-pixel | `line()` is simpler for multi-pixel ray segments. `point()` gives more control but is verbose. Use `line()` for the main ray body. |
| Linear alpha fade | Exponential or quadratic fade | Linear is simplest and predictable. At this scale (24px max visible height) the difference between linear and exponential is ~2-3 alpha levels at any point -- imperceptible on LED. Start with linear, adjust if needed. |

## Architecture Patterns

### Current SunAnimation Structure (what changes)
```
src/display/weather_anim.py
├── SunAnimation(WeatherAnimation)
│   ├── _SUN_X = 63              # unchanged (from Phase 9)
│   ├── _SUN_Y = 0               # unchanged
│   ├── _SUN_RADIUS = 8          # unchanged
│   ├── _draw_sun_body()         # unchanged (Phase 9)
│   ├── _spawn_far(9)            # REWRITE: polar ray init
│   ├── _spawn_near(5)           # REWRITE: polar ray init
│   ├── _draw_ray()              # REWRITE: polar drawing with fade
│   ├── tick()                   # UPDATE: new ray advancement
│   └── reset()                  # UPDATE: re-init polar rays
```

### Pattern 1: Polar Ray State
**What:** Each ray is a list of floats representing `[angle, distance, speed, max_distance, base_alpha]`. The angle is fixed for the ray's lifetime; distance advances each tick.
**When to use:** When particles need to radiate outward from a fixed origin point.
**Example:**
```python
# Source: Derived from codebase analysis + polar math verification
import math
import random

_SUN_X = 63
_SUN_Y = 0

# Fan range: 95 to 160 degrees (downward-facing from top-right corner)
_FAN_MIN = 95.0
_FAN_MAX = 160.0

def _make_ray(*, far: bool, stagger: bool = True) -> list[float]:
    """Create a single polar ray.

    Args:
        far: True for far/dim rays, False for near/bright rays.
        stagger: True to randomize initial distance (mid-flow start).
    """
    angle = random.uniform(_FAN_MIN, _FAN_MAX)
    if far:
        speed = random.uniform(0.3, 0.6)
        max_dist = random.uniform(20.0, 30.0)
        base_alpha = random.randint(90, 130)
    else:
        speed = random.uniform(0.5, 1.0)
        max_dist = random.uniform(15.0, 25.0)
        base_alpha = random.randint(150, 210)

    distance = random.uniform(0, max_dist) if stagger else 0.0
    return [angle, distance, speed, max_dist, float(base_alpha)]
```
**Confidence:** HIGH -- math verified experimentally with Python.

### Pattern 2: Distance-Based Alpha Fade
**What:** Alpha decreases linearly as the ray travels from origin to max_distance. The ray pixel is drawn only when the calculated alpha exceeds the LED visibility threshold.
**When to use:** When creating a light-emission / glow-from-source effect.
**Example:**
```python
# Source: Derived from codebase LED alpha constraints (weather_anim.py docstring)
def _tick_and_draw_ray(self, draw, ray, color_rgb):
    angle, distance, speed, max_dist, base_alpha = ray

    # Advance distance
    distance += speed
    ray[1] = distance

    # Check respawn conditions
    rad = math.radians(angle)
    x = self._SUN_X + math.cos(rad) * distance
    y = self._SUN_Y + math.sin(rad) * distance

    if distance >= max_dist or x < 0 or x >= self.width or y >= self.height:
        ray[1] = 0.0  # respawn at origin
        return

    # Distance-based alpha fade
    fade = 1.0 - (distance / max_dist)
    alpha = int(base_alpha * fade)

    if alpha < 15:  # below LED visibility threshold
        return

    # Draw ray segment (short line from current pos toward origin)
    x1, y1 = int(x), int(y)
    # Tail: a few pixels back along the ray direction
    tail_len = 2 if base_alpha < 140 else 3  # far=shorter, near=longer
    tx = x - math.cos(rad) * tail_len
    ty = y - math.sin(rad) * tail_len
    x2, y2 = int(max(0, min(tx, self.width - 1))), int(max(0, min(ty, self.height - 1)))

    if 0 <= x1 < self.width and 0 <= y1 < self.height:
        draw.line([(x2, y2), (x1, y1)], fill=(*color_rgb, alpha))
```
**Confidence:** HIGH -- alpha ranges verified against codebase LED threshold documentation.

### Pattern 3: Staggered Initialization (ANIM-07)
**What:** On `__init__()` and `reset()`, each ray's initial distance is `random.uniform(0, max_distance)` rather than 0. This distributes rays across the full travel path.
**When to use:** When animation must appear "already running" from the first frame.
**Example:**
```python
# Source: Pattern used by ClearNightAnimation star initialization (weather_anim.py:568-577)
# Stars start at random state machine positions -- same principle for ray distances
distance = random.uniform(0, max_dist)  # not 0.0
```
**Confidence:** HIGH -- same staggering pattern already proven in ClearNightAnimation.

### Anti-Patterns to Avoid
- **Cartesian-origin random spawning:** The CURRENT approach spawns rays at random `(x, 0)` positions across the full zone width. This produces disconnected diagonal streaks rather than radial emission. The whole point of Phase 10 is replacing this with polar coordinates anchored at (63, 0).
- **All rays at same angle:** Would look like a single thick beam, not a fan of sunlight. Must distribute across the 95-160 degree range.
- **All rays at distance=0 on init:** Creates a visible burst/explosion effect on first frame. Must stagger (ANIM-07).
- **Forgetting to draw the sun body:** `_draw_sun_body()` must still be called in `tick()`. Only the ray spawning/drawing changes.
- **Using `putpixel()` instead of `ImageDraw`:** Direct pixel access is slower and doesn't integrate with the draw pipeline. Use `draw.line()` or `draw.point()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Polar-to-cartesian math | Custom lookup tables or integer approximations | `math.cos()`/`math.sin()` on `math.radians()` | Standard library is fast enough for 14 rays at 1 FPS. No optimization needed. |
| Line rasterization | Manual Bresenham line drawing | PIL `ImageDraw.line()` | Already handles sub-pixel clipping, anti-aliasing edge cases. Same tool used by all other animations. |
| Alpha compositing | Manual pixel-by-pixel blending | PIL `Image.alpha_composite()` | The renderer's `_composite_layer()` already handles this. Ray just needs to set RGBA fill values. |

**Key insight:** The ray system is purely a state-model change (cartesian random -> polar radial) with the same PIL drawing primitives used by every other animation. No new rendering capabilities needed.

## Common Pitfalls

### Pitfall 1: Fan Angle Range Too Wide or Too Narrow
**What goes wrong:** Too wide (e.g., 0-360) sends rays upward and rightward off-screen immediately. Too narrow (e.g., 120-140) produces a thin beam instead of a fan.
**Why it happens:** The sun is at the top-right CORNER, not center. Only the downward-left quadrant of the circle is visible within the 64x24 zone.
**How to avoid:** Use 95-160 degrees. Verified mathematically: 90 degrees = straight down (hits zone bottom at 23px distance), 160 degrees = toward bottom-left corner (hits zone bottom at 48px distance). This produces a 65-degree-wide fan that covers the visible zone diagonally.
**Warning signs:** Rays exiting the zone within 1-2 ticks of spawning, or visible gaps where no rays travel.

### Pitfall 2: Alpha Fade Below LED Visibility Too Early
**What goes wrong:** Rays become invisible before reaching mid-zone, making the animation look like short stubs near the sun rather than full-zone beams.
**Why it happens:** LED pixels below ~RGB(15,15,15) produce no visible light. If base_alpha is low (e.g., 80) and max_distance is long (e.g., 40), the ray hits alpha=15 at only 30% of its travel distance.
**How to avoid:** Far rays: base_alpha 90-130 with max_distance 20-30. Near rays: base_alpha 150-210 with max_distance 15-25. This ensures rays remain visible through at least 50-70% of their travel. The fade tail (below threshold) creates a natural disappearing edge.
**Warning signs:** Rays visible in debug PNG but invisible on LED hardware past a certain distance.

### Pitfall 3: Rays Moving Too Fast at 1 FPS
**What goes wrong:** At 1 FPS, a ray moving 2px per tick traverses the 24px zone height in 12 seconds. If speed is too high (>1.5px/tick), rays cross the zone in under 15 seconds and the animation looks frantic rather than ambient.
**Why it happens:** Other particle animations (rain at 2-3px/tick) work because rain is supposed to look fast. Sun rays should feel slow and warm.
**How to avoid:** Far rays: 0.3-0.6 px/tick (40-80 seconds per full cycle). Near rays: 0.5-1.0 px/tick (25-50 seconds per full cycle). This gives a calm, ambient radiating effect.
**Warning signs:** Rays visibly jumping between frames instead of gliding.

### Pitfall 4: Breaking the Sun Body Drawing
**What goes wrong:** Removing or reordering `self._draw_sun_body(bg_draw)` from `tick()` while rewriting the ray code causes the sun body to disappear.
**Why it happens:** The sun body is drawn in the same `tick()` method as the rays. Easy to accidentally delete during the rewrite.
**How to avoid:** Keep the `self._draw_sun_body(bg_draw)` call at the top of `tick()` before any ray drawing. Verify with existing `TestSunBody` tests which check for warm pixels at the sun position.
**Warning signs:** `TestSunBody::test_sun_body_produces_warm_pixels_at_position` fails.

### Pitfall 5: Respawning All Rays Simultaneously
**What goes wrong:** If multiple rays happen to reach max_distance on the same tick, they all respawn at distance=0 together, creating a periodic "burst" effect.
**Why it happens:** Rays with similar speeds and max_distances will synchronize over time.
**How to avoid:** Randomize max_distance per ray (e.g., 20-30 for far, 15-25 for near). Randomize speed per ray. On respawn, optionally re-randomize both. The combination of varied speeds and distances prevents synchronization.
**Warning signs:** Periodic visible clusters of rays near the sun origin, followed by sparse mid-zone.

### Pitfall 6: Existing Tests Expecting Old Ray Structure
**What goes wrong:** Tests that check `len(anim.far_rays)` or `anim.far_rays[i][0]` (x position) will break because the ray data structure changes from `[x, y, speed, length, alpha]` to `[angle, distance, speed, max_distance, base_alpha]`.
**Why it happens:** The `TestSunBody::test_sun_animation_still_has_rays` test uses `_sample_particle_rgb()` which ticks the animation and checks for non-transparent pixels. This should still work since rays are still drawn. But any test directly inspecting ray list structure would break.
**How to avoid:** Check existing tests before modifying ray lists. The current `test_sun_animation_still_has_rays` only checks pixel output (not list structure), so it should pass unchanged. Add new TEST-02 test for ray origin clustering.
**Warning signs:** `test_sun_animation_still_has_rays` failing after ray refactor.

## Code Examples

### Example 1: Complete Polar Ray Spawning
```python
# Source: Derived from existing _spawn_far/_spawn_near pattern + polar math analysis

# Class constants for fan geometry
_FAN_MIN_DEG = 95.0    # just past straight-down (avoids right-edge exit)
_FAN_MAX_DEG = 160.0   # toward bottom-left corner of zone

def _spawn_far(self, count: int) -> None:
    for _ in range(count):
        angle = random.uniform(self._FAN_MIN_DEG, self._FAN_MAX_DEG)
        speed = random.uniform(0.3, 0.6)
        max_dist = random.uniform(20.0, 30.0)
        base_alpha = random.randint(90, 130)
        distance = random.uniform(0, max_dist)  # staggered start
        self.far_rays.append([angle, distance, speed, max_dist, float(base_alpha)])

def _spawn_near(self, count: int) -> None:
    for _ in range(count):
        angle = random.uniform(self._FAN_MIN_DEG, self._FAN_MAX_DEG)
        speed = random.uniform(0.5, 1.0)
        max_dist = random.uniform(15.0, 25.0)
        base_alpha = random.randint(150, 210)
        distance = random.uniform(0, max_dist)  # staggered start
        self.near_rays.append([angle, distance, speed, max_dist, float(base_alpha)])
```

### Example 2: Polar Ray Drawing with Fade
```python
# Source: Derived from existing _draw_ray pattern + distance-fade analysis

def _draw_ray(self, draw: ImageDraw.Draw, ray: list[float], color: tuple) -> None:
    angle, distance, speed, max_dist, base_alpha = ray

    # Advance outward
    distance += speed
    ray[1] = distance

    # Convert polar to cartesian
    rad = math.radians(angle)
    x = self._SUN_X + math.cos(rad) * distance
    y = self._SUN_Y + math.sin(rad) * distance

    # Respawn if out of zone or past max distance
    if distance >= max_dist or x < 0 or x >= self.width or y < 0 or y >= self.height:
        ray[1] = 0.0  # reset distance to respawn at origin
        return

    # Distance-based alpha fade
    fade = 1.0 - (distance / max_dist)
    alpha = int(base_alpha * fade)
    if alpha < 15:
        return

    # Draw ray segment: short line trailing back toward origin
    x1, y1 = int(x), int(y)
    tail_len = 2 if base_alpha < 140 else 3
    tx = x - math.cos(rad) * tail_len
    ty = y - math.sin(rad) * tail_len
    x2 = int(max(0, min(tx, self.width - 1)))
    y2 = int(max(0, min(ty, self.height - 1)))

    if 0 <= x1 < self.width and 0 <= y1 < self.height:
        draw.line([(x2, y2), (x1, y1)], fill=(*color, alpha))
```

### Example 3: Updated tick() Method
```python
# Source: Derived from existing SunAnimation.tick() structure

def tick(self) -> tuple[Image.Image, Image.Image]:
    bg = self._empty()
    fg = self._empty()
    bg_draw = ImageDraw.Draw(bg)
    fg_draw = ImageDraw.Draw(fg)

    # Sun body behind text (unchanged from Phase 9)
    self._draw_sun_body(bg_draw)

    # Far rays on bg layer (behind text)
    for ray in self.far_rays:
        self._draw_ray(bg_draw, ray, (240, 200, 40))

    # Near rays on fg layer (in front of text)
    for ray in self.near_rays:
        self._draw_ray(fg_draw, ray, (255, 240, 60))

    return bg, fg
```

### Example 4: TEST-02 Ray Origin Clustering Test
```python
# Source: Derived from existing test patterns in test_weather_anim.py

def test_ray_origin_clustering(self):
    """Rays should cluster near sun origin, not be randomly scattered.

    After several ticks, most ray head positions should be closer to the
    sun center (63, 0) than the zone center (32, 12).
    """
    import math
    anim = SunAnimation()

    # Tick several times to let rays distribute
    for _ in range(10):
        anim.tick()

    # Collect current ray head positions
    sun_x, sun_y = SunAnimation._SUN_X, SunAnimation._SUN_Y
    distances_from_sun = []

    for ray in anim.far_rays + anim.near_rays:
        angle, distance, speed, max_dist, base_alpha = ray
        rad = math.radians(angle)
        x = sun_x + math.cos(rad) * distance
        y = sun_y + math.sin(rad) * distance
        dist = math.sqrt((x - sun_x) ** 2 + (y - sun_y) ** 2)
        distances_from_sun.append(dist)

    avg_dist = sum(distances_from_sun) / len(distances_from_sun)
    # Rays should average less than half the zone diagonal (~34px)
    # A random distribution across 64x24 would average ~25-30px from corner
    assert avg_dist < 20.0, (
        f"Average ray distance from sun ({avg_dist:.1f}px) too large -- "
        f"rays should cluster near origin, not scatter randomly"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Random cartesian spawning `[x, y, speed, length, alpha]` at any x position | Polar ray spawning `[angle, distance, speed, max_dist, base_alpha]` from (63, 0) | Phase 10 (this phase) | Rays visibly radiate from sun instead of falling as disconnected diagonal streaks |
| Constant alpha per ray (set at spawn) | Distance-proportional alpha fade `base_alpha * (1 - distance/max_dist)` | Phase 10 (this phase) | Natural light-emission falloff effect |
| All rays start at y=0 top of zone | Staggered initial distances across full travel path | Phase 10 (this phase) | Animation appears "already running" from first frame |
| Fixed downward motion `ray[1] += speed` | Polar advancement `distance += speed` with angle-based cartesian conversion | Phase 10 (this phase) | Radial fan spread instead of parallel downward motion |

**Deprecated/outdated:**
- The cartesian `_draw_ray()` method with `ray[0] += speed * 0.4; ray[1] += speed` (diagonal downward motion) -- replaced with polar distance advancement.
- Random x-position spawning via `random.randint(0, self.width - 1)` -- replaced with angle-based spawning from sun center.

## Open Questions

1. **Exact fan angle range (95-160 vs wider/narrower)**
   - What we know: 95-160 degrees covers the visible zone from straight-down to bottom-left corner. Verified mathematically.
   - What's unclear: Whether the visual result looks "sunny" enough or needs wider spread. Very narrow fan (e.g., 110-140) might look more focused and intense.
   - Recommendation: Start with 95-160 (wide fan). These are class constants, trivially adjustable during UAT.

2. **Ray segment length (tail pixels)**
   - What we know: Current rays draw a line segment of 2-7 pixels. New polar rays need a tail length too -- how many pixels trailing back toward the origin.
   - What's unclear: Whether 2px (far) / 3px (near) tails are visible enough at 1 FPS on LED, or if longer tails (4-5px) look better.
   - Recommendation: Start with 2px far / 3px near. Match the current far/near length differentiation pattern.

3. **Speed re-randomization on respawn**
   - What we know: Current rays keep the same speed forever. Re-randomizing on respawn (like ClearNightAnimation re-randomizes star durations) would add organic variety.
   - What's unclear: Whether the visual benefit is noticeable with only 14 rays at 1 FPS.
   - Recommendation: Re-randomize angle, speed, and max_distance on respawn. Low implementation cost, adds organic feel, prevents synchronization (Pitfall 5).

4. **Near ray parallax speed vs far ray speed**
   - What we know: Current system has near rays 1.5-2x faster than far rays. Rain/snow use this for depth parallax.
   - What's unclear: Whether the same ratio works for radial rays or if a different ratio looks better.
   - Recommendation: Keep the ~1.5-2x ratio. Far: 0.3-0.6, Near: 0.5-1.0. Same depth-parallax principle as other animations.

## Sources

### Primary (HIGH confidence)
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/weather_anim.py` - Current SunAnimation implementation (lines 276-379), all animation classes, ray state structure, tick/draw patterns, compositing pipeline
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/renderer.py` - Weather zone 3D layer compositing: bg layer -> text -> fg layer (lines 122-208)
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/layout.py` - Zone definitions: WEATHER_ZONE x=0, y=40, w=64, h=24
- `/Users/jdl/Documents/GitHub/divoom-hub/tests/test_weather_anim.py` - Existing TestSunBody (4 tests), animation test patterns, color identity tests, particle sampling helper
- Direct Python math verification - Polar-to-cartesian ray trajectories verified for all angles 90-200 degrees at 1-50px distances, zone boundary intersection points computed

### Secondary (MEDIUM confidence)
- Phase 9 research and implementation - Corner-anchored sun body at (63, 0) with r=8, two-layer glow. Established the origin point for radial rays.
- ClearNightAnimation stagger pattern - Stars initialized at random state machine positions (lines 568-577). Same principle applied to ray distance staggering.

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, pure PIL drawing + Python math (already in codebase)
- Architecture: HIGH - Modifying existing SunAnimation with well-understood polar math, same draw pipeline, same depth layer system
- Pitfalls: HIGH - All pitfalls identified from direct codebase analysis, mathematical verification, and LED hardware constraints documented in codebase

**Research date:** 2026-02-23
**Valid until:** 2026-03-25 (stable domain -- PIL drawing, trigonometry, LED animation patterns)
