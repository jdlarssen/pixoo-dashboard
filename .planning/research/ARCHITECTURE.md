# Architecture Research: Radial Sun Ray Integration

**Domain:** v1.2 Sun Ray Overhaul -- radial beam system replacing random sky-wide rays
**Researched:** 2026-02-23
**Confidence:** HIGH (existing codebase fully audited, integration points clearly bounded)

## Current SunAnimation Architecture (What Exists)

```
SunAnimation(WeatherAnimation)
  __init__():
    far_rays: list[list[float]]   # 9 rays, each [x, y, speed, length, alpha]
    near_rays: list[list[float]]  # 5 rays, each [x, y, speed, length, alpha]

  _spawn_far(9):  random x across 0..63, random y across 0..23, diagonal fall
  _spawn_near(5): random x across 0..63, random y across 0..23, diagonal fall

  _draw_ray():    line from (x,y) angled down-right, advances y+speed, x+speed*0.4
                  respawns at y=0 random x when past bottom/right edge

  _draw_sun_body(): ellipse at (48, 4) radius 3 with glow ring at radius 4
                    drawn on bg_layer only

  tick():
    bg = _empty() + sun_body + far_rays
    fg = _empty() + near_rays
    return (bg, fg)
```

### Current Sun Constants

```python
_SUN_X = 48        # center x of sun circle
_SUN_Y = 4         # center y of sun circle
_SUN_RADIUS = 3    # 7px diameter circle
```

### Current Ray Behavior (Problems to Fix)

1. **Rays spawn at random positions across entire 64x24 zone** -- no visual connection to the sun body
2. **All rays move in same direction** (down-right at ~30 degrees) -- looks like diagonal rain in yellow
3. **Rays respawn at y=0 with random x** -- again, no relationship to sun position
4. **Sun body is a full circle** at y=4 -- but requirement calls for a half-sun clipped at top edge

## Target Architecture (v1.2 Radial System)

```
SunAnimation(WeatherAnimation)   # same class, rewritten internals
  __init__():
    far_rays: list[dict]          # 9 rays, radial origin from sun
    near_rays: list[dict]         # 5 rays, radial origin from sun

  Sun body:
    Half-semicircle at top-right, center at (48, 0), radius 7
    Only bottom half visible (clipped by zone top edge at y=0)

  Ray behavior:
    Spawn at sun center (48, 0)
    Emit at random angles (downward hemisphere: ~90-270 degrees from up)
    Travel outward along their angle
    Fade alpha with distance from sun
    Respawn at origin when past zone bounds or fully faded
```

### System Overview: What Changes vs What Stays

```
UNCHANGED (do not touch):
  +--------------------------------------------------+
  | WeatherAnimation base class                       |
  | .tick() -> (bg_layer, fg_layer) contract          |
  | .reset() contract                                 |
  | ._empty() -> 64x24 RGBA transparent image         |
  | .width / .height (64x24)                          |
  +--------------------------------------------------+
  | get_animation() factory                            |
  |   "clear" -> SunAnimation  (still maps here)     |
  |   "partcloud" -> SunAnimation (still maps here)   |
  | _ANIMATION_MAP, _NIGHT_ANIMATION_MAP              |
  +--------------------------------------------------+
  | renderer.py: render_weather_zone()                |
  |   _composite_layer(bg) -> text -> _composite(fg)  |
  | main.py: weather_anim.tick() call, 1 FPS loop     |
  | CompositeAnimation, WindEffect wrappers            |
  | All other animation classes (Rain, Snow, etc.)     |
  +--------------------------------------------------+

MODIFIED (SunAnimation internals only):
  +--------------------------------------------------+
  | SunAnimation._SUN_X = 48                          |
  | SunAnimation._SUN_Y = 0  (was 4)                 |
  | SunAnimation._SUN_RADIUS = 7  (was 3)            |
  +--------------------------------------------------+
  | _draw_sun_body() -> half-semicircle, not circle   |
  | _spawn_far() -> radial angle + distance params    |
  | _spawn_near() -> radial angle + distance params   |
  | _draw_ray() -> radial line from sun outward       |
  | tick() -> same (bg, fg) contract, new visuals     |
  | reset() -> same contract, new spawn logic         |
  +--------------------------------------------------+

MODIFIED (test updates):
  +--------------------------------------------------+
  | test_weather_anim.py::TestSunBody                 |
  |   Pixel position assertions update for new geom   |
  | test_weather_anim.py::TestAnimationVisibility     |
  |   sun alpha thresholds may need adjustment        |
  | test_weather_anim.py::TestColorIdentity           |
  |   sun yellow dominance test should still pass     |
  +--------------------------------------------------+
```

## Component Responsibilities

| Component | Responsibility | v1.2 Change? |
|-----------|---------------|--------------|
| `WeatherAnimation` (base) | Define 64x24 RGBA layer contract | NO -- untouched |
| `SunAnimation` | Produce sun body + ray particles as (bg, fg) | YES -- rewrite internals |
| `get_animation()` factory | Map weather codes to animation classes | NO -- still returns SunAnimation for clear/partcloud |
| `_ANIMATION_MAP` dict | Weather group -> class mapping | NO |
| `renderer.py` | Composite bg behind text, fg in front | NO -- consumes same (bg, fg) tuple |
| `main.py` main_loop | Call weather_anim.tick() at 1 FPS | NO |
| `layout.py` | Zone definitions, color constants | NO -- sun colors are inline in weather_anim.py |
| `test_weather_anim.py` | Visibility, color identity, sun body assertions | YES -- update geometry assertions |

## Integration Points

### Integration Point 1: SunAnimation.__init__()

**Current:** Creates `far_rays` and `near_rays` as `list[list[float]]` where each ray is `[x, y, speed, length, alpha]`.

**New:** Each ray needs angle, distance-from-sun, and radial speed instead of cartesian velocity. Use a dict for clarity:

```python
# New ray data structure
{
    "angle": float,      # radians, emission direction from sun center
    "dist": float,       # current distance from sun center (starts ~radius)
    "speed": float,      # pixels per tick outward travel
    "length": float,     # ray line length in pixels
    "max_alpha": int,    # peak alpha at sun body (fades with distance)
}
```

**Why dict over list:** The existing ray list `[x, y, speed, length, alpha]` uses positional indexing (`ray[0]`, `ray[1]`, etc.) which is fragile. Switching to dicts aligns with the pattern already used by `ClearNightAnimation` stars (which use dicts with named keys). This is an internal change -- no external API impact.

**Impact:** `far_rays` and `near_rays` change from `list[list[float]]` to `list[dict]`. The `WindEffect` wrapper checks for `far_rays` attribute on inner animations but only for rain/snow (`far_drops`, `near_drops`, `far_flakes`, `near_flakes`). Sun rays are not wind-affected, so `WindEffect` never touches them. No compatibility issue.

### Integration Point 2: _draw_sun_body()

**Current:** Full ellipse at (48, 4) with radius 3 + glow ring at radius 4. Drawn on `bg_draw` (behind text).

**New:** Half-semicircle at (48, 0) with radius 7. Only the bottom half is visible because the center is at the zone's top edge (y=0). The top half of the circle is clipped by the zone boundary.

```python
# Current: full circle, small
draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=...)

# New: draw full circle but center at y=0, so top half is clipped by zone bounds
# PIL will naturally clip anything drawn at negative y coordinates.
# Center at (48, 0), radius 7 means:
#   ellipse bbox = [41, -7, 55, 7]
#   Only y=0..7 portion is visible = bottom semicircle
```

**PIL clipping behavior:** PIL's `ImageDraw.ellipse()` draws within the image bounds automatically. Coordinates outside the image (y < 0) are simply not rendered. This means drawing a circle centered at y=0 produces a half-circle with zero extra code -- PIL handles the clipping.

**Why bg_layer:** Sun body stays on bg_layer (behind text) same as today. This preserves readability of weather text on the left side. The sun is at x=48, well right of the text at x=2.

### Integration Point 3: _draw_ray()

**Current:** Takes a ray list, draws a line from (x, y) angled down-right, advances position each tick, respawns at y=0 when past bounds.

**New:** Converts polar (angle, distance) to cartesian for drawing. Draws a line from the ray's current position outward along its angle. Alpha fades proportionally with distance from sun.

```python
def _draw_ray(self, draw: ImageDraw.Draw, ray: dict, base_color: tuple) -> None:
    angle = ray["angle"]
    dist = ray["dist"]
    length = ray["length"]
    max_alpha = ray["max_alpha"]

    # Convert polar to cartesian (origin = sun center)
    cx = self._SUN_X + dist * math.cos(angle)
    cy = self._SUN_Y + dist * math.sin(angle)

    # Ray endpoint (extends further along same angle)
    ex = self._SUN_X + (dist + length) * math.cos(angle)
    ey = self._SUN_Y + (dist + length) * math.sin(angle)

    # Fade alpha with distance (linear falloff)
    max_dist = max(self.width, self.height)  # ~64px
    alpha = int(max_alpha * max(0, 1 - dist / max_dist))

    if alpha > 0:
        draw.line(
            [(int(cx), int(cy)), (int(ex), int(ey))],
            fill=(*base_color, alpha),
        )

    # Advance outward
    ray["dist"] += ray["speed"]

    # Respawn when past zone bounds or fully faded
    if dist > max_dist or alpha <= 0:
        self._respawn_ray(ray)
```

**Key change:** Rays now move outward from sun center instead of falling downward. Alpha fades with distance instead of being constant. This creates the visual effect of rays "beaming" outward.

### Integration Point 4: tick() Return Contract

**Unchanged.** `tick()` still returns `(bg_layer, fg_layer)` as RGBA 64x24 images:
- `bg_layer`: sun body + far rays (behind text)
- `fg_layer`: near rays (in front of text)

The renderer's `render_weather_zone()` composites these layers identically to today. Zero changes needed in renderer.py.

### Integration Point 5: Angle Distribution for Emission

**New logic needed.** Rays must emit into the downward hemisphere since the sun is at the top of the zone. Angles should cover approximately 0 to pi radians (right side, downward, left side). Rays emitting upward (negative y) would be invisible since the sun is at y=0.

```python
# Emission angle range: pi/6 to 5*pi/6 (30 to 150 degrees)
# This avoids near-horizontal rays that look unnatural
# and covers the visible downward fan
angle = random.uniform(math.pi / 6, 5 * math.pi / 6)
```

Using `pi/6` to `5*pi/6` (30 to 150 degrees in standard math angles where 0=right, pi/2=down) ensures rays fan out below the sun body. Purely horizontal rays (angle=0 or pi) would be hard to see and look wrong.

### Integration Point 6: Respawn Logic

**Current:** Ray respawns at y=0 with random x when past bottom edge.

**New:** Ray respawns at the sun body's edge (distance = sun radius) with a new random angle. This creates continuous emission from the sun.

```python
def _respawn_ray(self, ray: dict) -> None:
    ray["angle"] = random.uniform(math.pi / 6, 5 * math.pi / 6)
    ray["dist"] = float(self._SUN_RADIUS)  # start at sun's edge
    ray["speed"] = random.uniform(...)       # far vs near speed
    ray["length"] = random.randint(...)      # far vs near length
```

### Integration Point 7: Test Assertions

**Tests that need updating:**

| Test | Current Assertion | New Assertion |
|------|-------------------|---------------|
| `test_sun_body_produces_warm_pixels_at_position` | Checks pixel at `(SUN_X=48, SUN_Y=4)` for warm yellow | Check pixel at `(48, 0)` or `(48, 3)` -- wherever the half-circle center/visible portion is |
| `test_sun_body_has_glow` | Checks pixel at `(SUN_X - R - 1, SUN_Y)` = `(44, 4)` | Check glow at new position, accounting for half-circle geometry |
| `test_sun_animation_still_has_rays` | Checks particle count > 10 | Should still pass -- same or more ray particles |
| `test_sun_alpha_above_minimum` | `max_alpha >= 100` | Should still pass -- sun body alpha is 200+ |
| `test_sun_particles_are_yellow_dominant` | R > B+50, G > B+30 | Should still pass -- same yellow color palette |

**Tests that should pass without changes:**

| Test | Why Safe |
|------|----------|
| `test_tick_returns_two_layers` | Contract unchanged -- still returns (bg, fg) RGBA 64x24 |
| `test_get_animation_returns_correct_types` | SunAnimation not tested here (clear/partcloud mapped, not direct) |
| `test_clear_day_returns_sun_animation` | Still returns SunAnimation instance |
| `test_clear_day_unaffected_by_wind` | SunAnimation still not wind-applicable |
| All color identity tests | Yellow dominance preserved |
| All animation combo tests | SunAnimation not involved in composites/wind |

## Data Flow

### Rendering Pipeline (Unchanged)

```
main_loop (1 FPS)
    |
    v
weather_anim.tick()
    |
    +--> SunAnimation.tick()
    |      |
    |      +--> bg = _empty()           # 64x24 RGBA transparent
    |      +--> _draw_sun_body(bg_draw)  # half-circle at (48, 0) r=7
    |      +--> for ray in far_rays:
    |      |      _draw_ray(bg_draw, ray, (240, 200, 40))
    |      +--> for ray in near_rays:
    |      |      _draw_ray(fg_draw, ray, (255, 240, 60))
    |      +--> return (bg, fg)
    |
    v
render_frame(state, fonts, anim_frame=(bg, fg))
    |
    v
render_weather_zone(draw, img, state, fonts, anim_layers=(bg, fg))
    |
    +--> _composite_layer(img, bg, zone_y=40)     # bg behind text
    +--> draw.text(temperature, ...)                # weather text
    +--> draw.text(high/low, ...)
    +--> draw.text(rain_mm, ...)
    +--> _composite_layer(img, fg, zone_y=40)      # fg in front of text
    |
    v
client.push_frame(64x64 RGB image)
```

**The only code change is inside `SunAnimation`.** Everything upstream (main_loop timing, animation selection) and downstream (compositing, rendering, device push) is untouched.

### Coordinate System

```
Weather zone: 64x24 pixels (x: 0-63, y: 0-23)
Zone y=0 is at display y=40 (WEATHER_ZONE.y)

Sun position in zone coordinates:
  Center: (48, 0) -- top edge, right side
  Radius: 7
  Visible portion: bottom semicircle from y=0 to y=7

Text positions in zone coordinates:
  Temperature: (2, 1)
  High/low: (2, 10)
  Rain mm: (2, 17)

Rays emit from (48, 0) into the zone below.
Text is at x=2..~30, sun is at x=41..55.
Minimal overlap -- rays may pass through text area, which is the intended
3D depth effect (far rays behind text, near rays in front).
```

## Architectural Patterns

### Pattern 1: Polar-to-Cartesian Particle System

**What:** Store ray state in polar coordinates (angle + distance from origin) and convert to cartesian (x, y) only for drawing. All movement is in the radial direction (increasing distance).

**Why:** Radial emission from a point source is naturally expressed in polar coordinates. Cartesian math would require computing angles retroactively and makes respawning awkward.

**Trade-offs:** Slightly more math per ray (two cos/sin calls per tick per ray). With 14 total rays at 1 FPS, this is ~28 trig calls per second -- negligible.

### Pattern 2: Distance-Based Alpha Fade

**What:** Ray alpha decreases linearly with distance from sun center. At distance=0 (sun body), alpha is at maximum. At distance=max_dist, alpha is 0.

**Why:** Creates the natural visual of rays being brightest near the sun and fading into the sky. Without fade, rays look like random lines.

**Trade-offs:** Linear fade is simple and predictable. Exponential fade would look more realistic but is harder to tune for LED visibility. Start with linear, adjust if needed.

### Pattern 3: Dict-Based Particle State (Matching ClearNightAnimation)

**What:** Use dicts with named keys for ray state instead of positional lists.

**Why:** `ClearNightAnimation` already uses this pattern for stars (`{"x": ..., "y": ..., "peak_alpha": ..., "state": ...}`). The sun ray system has similar complexity (angle, distance, speed, length, max_alpha). Named keys prevent bugs from positional indexing.

**Existing precedent:**
```python
# ClearNightAnimation uses dicts:
star = {"x": 10, "y": 5, "peak_alpha": 200, "state": 0, "timer": 3, ...}

# Rain/Snow use lists:
drop = [x, y]   # simple 2-element list, positional is fine

# New sun rays are complex enough to warrant dicts:
ray = {"angle": 1.2, "dist": 5.0, "speed": 1.5, "length": 4, "max_alpha": 180}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adding a New Animation Class

**What:** Creating `RadialSunAnimation` as a separate class alongside `SunAnimation`.
**Why bad:** The factory `_ANIMATION_MAP` maps `"clear" -> SunAnimation`. Changing the map or adding a new class means modifying the factory, all tests that check `isinstance(anim, SunAnimation)`, and potentially breaking the `get_animation()` contract. It is unnecessary complexity -- this is a rewrite of internals, not a new animation type.
**Instead:** Modify `SunAnimation` in place. Same class, same external interface, new internal behavior.

### Anti-Pattern 2: Changing the (bg, fg) Layer Contract

**What:** Making SunAnimation return a third layer, or changing the layer semantics.
**Why bad:** The entire rendering pipeline in `renderer.py` is built around exactly two layers: bg composited before text, fg composited after text. Changing this contract ripples through `render_weather_zone()`, `render_frame()`, and all tests.
**Instead:** Work within the existing two-layer system. Sun body + far rays on bg, near rays on fg. This is the same split as today.

### Anti-Pattern 3: Modifying the Weather Zone Size

**What:** Expanding the weather zone to accommodate a larger sun.
**Why bad:** The zone pixel budget is exactly `11 + 8 + 1 + 19 + 1 + 24 = 64px`. Changing any zone disrupts the entire layout. The weather zone is 64x24 and that is fixed.
**Instead:** Design the half-sun and rays to fit within 64x24. A radius-7 semicircle occupies 15x7 pixels -- fits easily in the 64x24 zone.

### Anti-Pattern 4: Touching Other Animations

**What:** "While we're in weather_anim.py, let's also improve rain/cloud/snow..."
**Why bad:** Scope creep. The milestone is specifically about sun rays. Other animations were tuned and tested in v1.0/v1.1. Touching them risks regressions with no benefit to the stated goal.
**Instead:** Only modify `SunAnimation` and its test assertions.

## Build Order (Suggested Phase Structure)

### Phase 1: Sun Body Geometry

**What:** Change `_draw_sun_body()` from full circle at (48,4) r=3 to half-semicircle at (48,0) r=7.

**Files:** `src/display/weather_anim.py` (SunAnimation constants + `_draw_sun_body`)

**Why first:** The sun body is the visual anchor. Rays need to know where to emit from. Establishing the body position first means ray spawn logic can reference the correct constants.

**Verification:** `TEST_WEATHER=sun python src/main.py --simulated --save-frame`, inspect `debug_frame.png`.

**Tests:** Update `TestSunBody.test_sun_body_produces_warm_pixels_at_position` and `test_sun_body_has_glow` for new coordinates.

### Phase 2: Radial Ray System

**What:** Replace ray data structure and spawn/draw/advance/respawn logic with polar coordinate system. Distance-based alpha fade.

**Files:** `src/display/weather_anim.py` (SunAnimation `__init__`, `_spawn_far`, `_spawn_near`, `_draw_ray`, `tick`, `reset`)

**Why second:** Depends on Phase 1 for sun center position. This is the core visual change.

**Verification:** `TEST_WEATHER=sun --save-frame`, multiple frames to see ray motion. Also `TEST_WEATHER=clear` to confirm it works through the factory.

**Tests:** Update `TestSunBody.test_sun_animation_still_has_rays`. Existing visibility and color identity tests should pass without changes (same alpha ranges, same yellow color family).

### Phase 3: Tuning and Test Finalization

**What:** Fine-tune ray count, speed ranges, alpha falloff curve, angle distribution, and ray lengths for visual quality on LED hardware. Finalize all test assertions.

**Files:** `src/display/weather_anim.py` (parameter values), `tests/test_weather_anim.py` (any remaining assertion fixes)

**Why third:** Tuning requires the system to be functional. Cannot tune what does not exist yet.

**Verification:** Physical LED hardware testing with `--save-frame` for before/after comparison.

### Dependency Graph

```
Phase 1: Sun Body Geometry
    |
    v
Phase 2: Radial Ray System (depends on Phase 1 for sun position)
    |
    v
Phase 3: Tuning + Tests (depends on Phase 2 for working system)
```

All three phases modify the same two files (`weather_anim.py` and `test_weather_anim.py`). No cross-file dependencies. No changes to any other module.

## File Change Summary

| File | Action | What Changes |
|------|--------|-------------|
| `src/display/weather_anim.py` | MODIFY | SunAnimation class internals only: constants, __init__, spawn, draw, tick, reset |
| `tests/test_weather_anim.py` | MODIFY | TestSunBody assertions for new geometry, possibly TestAnimationVisibility thresholds |

**Files NOT changed:**

| File | Why Not |
|------|---------|
| `src/display/renderer.py` | Consumes same (bg, fg) tuple -- no interface change |
| `src/display/layout.py` | Sun colors are inline in weather_anim.py, not in layout.py |
| `src/display/weather_icons.py` | Static 10px icons, unrelated to animation |
| `src/main.py` | Calls `weather_anim.tick()` generically -- no SunAnimation-specific code |
| `src/config.py` | No new config needed |
| All other animation classes | Rain, Snow, Cloud, Thunder, Fog, ClearNight, Composite, Wind -- untouched |
| All other test files | No renderer/layout/integration changes |

**Total scope: 2 files modified. Zero new files. Zero new dependencies.**

## Sources

- Codebase audit: all source files in `src/display/` and `tests/` read and analyzed (HIGH confidence)
- `SunAnimation` class: `src/display/weather_anim.py` lines 276-368 (HIGH confidence -- direct code reading)
- Renderer compositing: `src/display/renderer.py` `render_weather_zone()` lines 129-208 (HIGH confidence)
- Weather zone layout: `src/display/layout.py` WEATHER_ZONE at y=40, 64x24 (HIGH confidence)
- Test suite: `tests/test_weather_anim.py` TestSunBody, TestAnimationVisibility, TestColorIdentity (HIGH confidence)
- Main loop: `src/main.py` animation tick at 1 FPS (HIGH confidence)
- PIL ellipse clipping behavior: standard PIL/Pillow behavior, coordinates outside image bounds are clipped (HIGH confidence -- well-documented PIL behavior)
- Project requirements: `.planning/PROJECT.md` ANIM-01, ANIM-02, ANIM-03 (HIGH confidence)

---
*Architecture research for: Divoom Hub v1.2 Sun Ray Overhaul*
*Researched: 2026-02-23*
