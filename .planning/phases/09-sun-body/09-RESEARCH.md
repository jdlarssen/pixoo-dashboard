# Phase 9: Sun Body - Research

**Researched:** 2026-02-23
**Domain:** PIL/Pillow circle drawing, pixel-art rendering at 64x24 LED scale, weather zone compositing
**Confidence:** HIGH

## Summary

Phase 9 replaces the current small sun circle (`r=3` at `(48, 4)`) with a larger corner-anchored sun body placed at the top-right corner of the 64x24 weather zone. The sun center goes at approximately `(63, 0)` -- pushed to the corner so BOTH the top edge and right edge clip the circle, creating a quarter-sun sunrise arc. The visible portion should have a two-layer glow: a dimmer outer ring and a brighter warm-yellow inner fill.

The implementation is straightforward because PIL's `ImageDraw.ellipse()` naturally clips to image bounds. Drawing a circle centered at `(63, 0)` with a radius of 8-10 produces a recognizable quarter-sun arc in the top-right corner without any manual clipping code. The weather zone text (temp, hi/lo, rain) is entirely on the left side (starting at `x=2`), so there is zero overlap with the corner sun. Only Discord messages (starting at `x=22`) could extend into the sun region, but the sun is on the bg layer and text draws on top, which is acceptable.

The existing `SunAnimation` class in `src/display/weather_anim.py` needs its `_draw_sun_body()` method updated with new position, radius, and glow parameters. The existing ray code stays unchanged for now (Phase 10 handles ray overhaul). Tests in `tests/test_weather_anim.py::TestSunBody` need updating to assert the new position, radius, and boundary clipping.

**Primary recommendation:** Modify `SunAnimation._draw_sun_body()` to draw two concentric ellipses centered at `(63, 0)` -- inner body `r=8` at alpha ~200 and outer glow `r=10` at alpha ~60 -- relying on PIL's natural image-boundary clipping. No manual clipping needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Corner-anchored: sun center placed at the top-right corner of the weather zone, clipped by BOTH the top edge and right edge
- This creates a quarter-sun / corner sunrise arc rather than a half-circle peeking over just the top
- The original requirement spec of (48, 0) needs adjustment -- push center further right (e.g., toward 58-63, 0 or even beyond zone bounds) so both edges clip
- The visible arc should still be recognizable as a sun

### Claude's Discretion
- **Radius**: r=7 specified in requirements but may need adjustment for corner placement -- pick what gives the best visible arc
- **Smoothness**: Anti-aliased vs pixel-art edges -- decide based on what other display elements use
- **Color palette**: Warm yellow family -- choose specific hue, saturation, and color shift between inner/outer layers based on LED panel visibility
- **Inner brightness**: Alpha for inner body (current is 200) -- balance visibility vs LED bloom
- **Outer glow spread**: How many pixels beyond the body (+1-4px) -- pick what's visible without overwhelming the zone
- **Glow transition**: Hard step (two concentric shapes) vs smooth gradient -- decide based on what's achievable and visible at pixel scale
- **Outer glow alpha**: Must be above LED visibility threshold (~15) -- pick intensity that creates warmth without distraction
- **Clipping approach**: Draw full circle and let zone clip, or pre-clip -- pick what's cleanest to implement and test
- **Animation**: Static body or subtle pulse -- decide based on value vs noise at this scale
- **Text interaction**: Sun body layer placement (bg only, or split bg/fg), dimming under text overlap, ambient light effects -- decide based on actual text positions in the weather zone layout and readability
- **Text position check**: Verify where weather text (temp, hi/lo, description) renders relative to the top-right corner before deciding overlap strategy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANIM-01 | Sun appears as a half-sun semicircle (r=7) clipped at the top-right of the weather zone at (48, 0) | User decision overrides: corner-anchored at ~(63, 0), radius adjustable. PIL ellipse auto-clips to image bounds. Tested configurations at r=8, r=10 produce recognizable quarter-sun arcs. |
| ANIM-02 | Sun body has two-layer glow (outer dim, inner bright warm yellow) | Two concentric PIL ellipses: inner body (255, 220, 60, 200) and outer glow (255, 200, 40, 60). Existing `_draw_sun_body()` already uses this pattern at smaller scale. Glow spread of +2px proven visible in testing. |
| TEST-01 | Sun body tests updated for new position and radius | Existing `TestSunBody` class (3 tests) in `tests/test_weather_anim.py` must be updated: new `_SUN_X`, `_SUN_Y`, `_SUN_RADIUS` values, plus new boundary-clipping assertion. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow (PIL) | 12.1.1 | Image drawing, ellipse rendering, RGBA compositing | Already used for all display rendering. `ImageDraw.ellipse()` handles sub-pixel clipping to image bounds automatically. |

### Supporting
No additional libraries needed. All functionality is within Pillow and Python stdlib.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PIL ellipse (rasterized) | Manual pixel-by-pixel circle (Bresenham) | Hand-rolled gives pixel-level control but PIL ellipse already produces good results at this scale. No benefit. |
| Two concentric shapes (hard step glow) | Smooth gradient via multiple rings | At 8-10px radius on a 64x24 LED display, smooth gradients are invisible. Two concentric shapes (body + glow) is sufficient and simpler. |

## Architecture Patterns

### Current SunAnimation Structure
```
src/display/weather_anim.py
├── SunAnimation(WeatherAnimation)
│   ├── _SUN_X = 48          # → changes to 63
│   ├── _SUN_Y = 4           # → changes to 0
│   ├── _SUN_RADIUS = 3      # → changes to ~8
│   ├── _draw_sun_body()     # → updated with new coords + two-layer glow
│   ├── tick()               # bg/fg layer pipeline (unchanged)
│   └── reset()              # (unchanged)
```

### Pattern 1: PIL Natural Clipping
**What:** Draw a full circle via `ImageDraw.ellipse()` on the 64x24 RGBA image. PIL silently clips any pixels outside the image bounds.
**When to use:** When the shape's center is at or near the image edge and you want only the visible portion rendered.
**Example:**
```python
# Source: Verified by direct Pillow 12.1.1 testing
img = Image.new("RGBA", (64, 24), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
cx, cy, r = 63, 0, 8
# PIL clips automatically -- no manual boundary checks needed
draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 220, 60, 200))
```
**Confidence:** HIGH -- verified experimentally with Pillow 12.1.1.

### Pattern 2: Two-Layer Glow via Concentric Shapes
**What:** Draw the outer glow ellipse first (larger, dimmer), then the inner body ellipse on top (smaller, brighter). Both on the same bg layer.
**When to use:** When creating a glowing effect around a shape at pixel scale.
**Example:**
```python
# Source: Existing _draw_sun_body() pattern in weather_anim.py, lines 333-345
def _draw_sun_body(self, draw: ImageDraw.Draw) -> None:
    cx, cy, r = self._SUN_X, self._SUN_Y, self._SUN_RADIUS
    glow_r = r + 2
    # Outer glow (larger, dimmer)
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=(255, 200, 40, 60),
    )
    # Inner body (bright warm yellow)
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(255, 220, 60, 200),
    )
```

### Pattern 3: bg Layer Only for Sun Body
**What:** Draw the sun body entirely on the bg layer (behind text), not the fg layer.
**When to use:** The sun body is a background element that text should render over if they ever overlap.
**Evidence:** The current implementation already draws the sun body on bg only (line 354: `self._draw_sun_body(bg_draw)`). Weather text is composited after the bg layer in the renderer pipeline (`render_weather_zone()` in `renderer.py` lines 153-154, 178-199).

### Anti-Patterns to Avoid
- **Manual pixel-by-pixel boundary clipping:** PIL handles this automatically. Adding `if 0 <= x < width and 0 <= y < height` checks for ellipse drawing is unnecessary complexity.
- **Drawing sun on fg layer:** The sun body should stay behind text. Only rays (Phase 10) split across bg/fg for depth.
- **Gradient simulation with many concentric rings:** At this pixel scale (8-10px radius), more than 2 layers of glow is invisible on LED hardware. Keep it to 2 concentric shapes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circle clipping at image boundary | Manual coordinate clamping or mask-based clipping | PIL's built-in `ellipse()` which auto-clips | PIL handles edge pixels correctly; manual clipping risks off-by-one errors and is more code to test |
| Anti-aliased circles | Custom sub-pixel rendering | PIL's default ellipse rasterization | At 64x24 on LED, anti-aliasing is invisible. PIL's standard rasterizer is fine. |
| Smooth glow gradients | Multiple rings with decreasing alpha | Two concentric ellipses (body + glow) | Indistinguishable from gradients at this pixel density on LED hardware |

**Key insight:** The entire sun body implementation is ~15 lines of PIL drawing code. The complexity is in choosing the RIGHT parameters (position, radius, colors, alphas), not in the drawing code itself.

## Common Pitfalls

### Pitfall 1: Radius Too Small for Corner Placement
**What goes wrong:** Using the original r=7 from ANIM-01 with center at (63, 0) produces a very small visible arc (~52 visible pixels). May not be recognizable as a sun.
**Why it happens:** When the center is at the corner (clipped on two sides), you lose ~75% of the circle. Need larger radius to compensate.
**How to avoid:** Use r=8 to r=10. Testing shows r=8 at (63, 0) gives 64 body pixels and r=10 gives 98 body pixels -- both recognizable.
**Warning signs:** If the visible arc is less than ~50 pixels of body, it may look like a formless blob rather than a sun.

### Pitfall 2: Glow Alpha Below LED Visibility Threshold
**What goes wrong:** Outer glow with alpha < 15 produces no visible light on the Pixoo 64 LED matrix.
**Why it happens:** LED pixels below ~RGB(15, 15, 15) produce no visible light (documented in weather_anim.py module docstring).
**How to avoid:** Outer glow alpha should be at least 40-60. The existing glow uses alpha=80, which is well above threshold.
**Warning signs:** Glow appears in debug PNG but is invisible on actual LED hardware.

### Pitfall 3: Forgetting to Update Class Constants
**What goes wrong:** Changing `_draw_sun_body()` but leaving `_SUN_X`, `_SUN_Y`, `_SUN_RADIUS` class constants at old values. Tests and Phase 10 (ray system) reference these constants.
**Why it happens:** The ray system in `tick()` and tests in `TestSunBody` both reference these class attributes.
**How to avoid:** Update all three class constants first, then update the drawing method. Tests will verify the constants match the drawing.

### Pitfall 4: Breaking Existing Ray System
**What goes wrong:** Phase 9 changes to `SunAnimation` accidentally break the existing ray animation (spawning, movement, drawing).
**Why it happens:** Rays currently spawn across the full zone width (0 to width-1) and fall downward. They don't reference the sun position constants.
**How to avoid:** Only modify `_draw_sun_body()`, `_SUN_X`, `_SUN_Y`, `_SUN_RADIUS`. Don't touch `_spawn_far`, `_spawn_near`, `_draw_ray`, `tick()` ray loops. Ray overhaul is Phase 10.

### Pitfall 5: Tests Asserting Exact Pixel Values at Clipped Boundaries
**What goes wrong:** Tests checking `getpixel((63, 0))` may get unexpected values because PIL's ellipse rasterization at exact boundary corners can be inconsistent.
**Why it happens:** Rasterization of circles at pixel boundaries is approximate. The exact corner pixel (63, 0) may or may not be filled depending on the rasterizer's sub-pixel rules.
**How to avoid:** Test a pixel that's clearly within the visible arc (e.g., `(60, 2)` or `(58, 3)`) rather than at the exact corner.

## Code Examples

### Example 1: Updated _draw_sun_body() Method
```python
# Source: Derived from existing pattern in weather_anim.py:333-345
# Updated for corner-anchored position per user decisions

# Class constants (replace existing values)
_SUN_X = 63
_SUN_Y = 0
_SUN_RADIUS = 8

def _draw_sun_body(self, draw: ImageDraw.Draw) -> None:
    """Draw a warm sun arc anchored at the top-right corner of the weather zone.

    Two concentric ellipses provide a two-layer glow effect:
    - Outer: dimmer warm yellow glow extending beyond the body
    - Inner: bright warm yellow sun body

    PIL automatically clips pixels outside the 64x24 image bounds,
    creating the corner-anchored quarter-sun arc.
    """
    cx, cy, r = self._SUN_X, self._SUN_Y, self._SUN_RADIUS
    glow_r = r + 2
    # Outer glow (larger, dimmer)
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=(255, 200, 40, 60),
    )
    # Inner body (bright warm yellow)
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(255, 220, 60, 200),
    )
```

### Example 2: Updated Test Assertions
```python
# Source: Derived from existing TestSunBody in test_weather_anim.py:603-632

class TestSunBody:
    def test_sun_body_produces_warm_pixels_at_position(self):
        """Sun body should produce warm yellow pixels in visible arc area."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        # Check a pixel clearly within the visible arc (not at exact corner)
        pixel = bg.getpixel((58, 3))
        r, g, b, a = pixel
        assert a >= 150, f"Sun body alpha {a} too low at visible arc"
        assert r > b + 50, f"Sun body not warm yellow: R={r} B={b}"

    def test_sun_body_has_glow(self):
        """Sun body should have a softer glow around the core."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        # Check glow region (beyond body radius, within glow radius)
        cx, cy, r = SunAnimation._SUN_X, SunAnimation._SUN_Y, SunAnimation._SUN_RADIUS
        glow_x = cx - r - 1  # just outside body, in glow
        if 0 <= glow_x < 64:
            glow_pixel = bg.getpixel((glow_x, 2))
            _, _, _, a = glow_pixel
            assert a > 0, "No glow detected around sun body"

    def test_sun_body_clipped_at_boundary(self):
        """No sun pixels should exist above y=0 or right of x=63 (image bounds)."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        # PIL enforces this automatically -- image is 64x24
        assert bg.size == (64, 24)
        # Verify the sun IS visible (not entirely clipped)
        non_transparent = sum(
            1 for x in range(64) for y in range(24)
            if bg.getpixel((x, y))[3] > 0
        )
        assert non_transparent > 30, f"Sun barely visible: only {non_transparent} pixels"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Small full circle at (48, 4), r=3 | Corner-anchored quarter-sun at (63, 0), r=8 | Phase 9 (this phase) | Larger, more recognizable sun. Establishes anchor point for radial ray system in Phase 10. |
| Single glow ring (r+1 at alpha 80) | Two-layer glow (body r at alpha 200, glow r+2 at alpha 60) | Phase 9 (this phase) | More defined glow boundary. Clearer visual hierarchy between body and ambient light. |

**Deprecated/outdated:**
- The (48, 0) position from ANIM-01 requirement text -- superseded by user decision to corner-anchor at ~(63, 0).
- The r=7 from ANIM-01 -- adjustable per user discretion to accommodate corner placement.

## Open Questions

1. **Exact radius value (8 vs 10)**
   - What we know: r=8 at (63, 0) gives 64 body pixels; r=10 gives 98 body pixels. Both produce recognizable arcs.
   - What's unclear: Which looks better on actual LED hardware (debug PNG vs LED panel differ due to pixel diffusion).
   - Recommendation: Start with r=8 (conservative). Easy to adjust the constant later if it looks too small on hardware.

2. **Static vs subtle pulse animation**
   - What we know: The user listed this as Claude's discretion. At 1 FPS on a 64-pixel LED, subtle alpha pulsing may be invisible or create distracting flicker.
   - What's unclear: Whether a 10-20 alpha variation at 1 FPS would be perceivable on LED hardware.
   - Recommendation: Start static. Pulse can be added as a follow-up if desired -- it's a ~5 line change to modulate alpha by tick count.

3. **Discord message overlap handling**
   - What we know: Message text (x=22 to x=63, y=1-20) can overlap the sun arc. Sun is bg layer, text draws on top. The current composite pipeline already handles this correctly -- text overdraws bg.
   - What's unclear: Whether the warm sun glow behind message text helps or hurts readability.
   - Recommendation: No special handling needed. The existing compositor pipeline (bg layer -> text -> fg layer) already puts text on top of the sun. Monitor visually.

## Sources

### Primary (HIGH confidence)
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/weather_anim.py` - Current SunAnimation implementation (lines 276-368), all animation classes, compositing patterns
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/renderer.py` - Weather zone rendering pipeline, layer compositing order (lines 122-208)
- `/Users/jdl/Documents/GitHub/divoom-hub/src/display/layout.py` - Zone definitions (WEATHER_ZONE: x=0, y=40, w=64, h=24), text positions, color constants
- `/Users/jdl/Documents/GitHub/divoom-hub/tests/test_weather_anim.py` - Existing TestSunBody class (3 tests, lines 603-632), animation test patterns
- Direct Pillow 12.1.1 testing - Verified ellipse auto-clips to image bounds, tested multiple radius/position configurations

### Secondary (MEDIUM confidence)
- Visual testing of radius/position configurations - ASCII art visualization of r=8/r=10 at (63,0) confirmed recognizable quarter-sun arcs

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pillow is already the rendering engine, no new dependencies
- Architecture: HIGH - Modifying an existing method with a well-understood pattern, verified by codebase inspection
- Pitfalls: HIGH - All pitfalls identified from direct codebase analysis and experimentation

**Research date:** 2026-02-23
**Valid until:** 2026-03-25 (stable domain -- Pillow API, pixel-art rendering)
