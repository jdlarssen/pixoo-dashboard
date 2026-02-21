# Phase 7: Weather Color Fix - Research

**Researched:** 2026-02-21
**Domain:** LED display color tuning, RGBA compositing, color contrast for pixel art
**Confidence:** HIGH

## Summary

Phase 7 is a focused color tuning task across two files (`weather_anim.py` for particle RGB values, `layout.py` for text color constants) plus a behavioral change to precipitation text display (number-only when >0mm) and new color-identity regression tests. The codebase architecture is well-understood from v1.0, the compositing pipeline is proven and must not be touched, and the specific problem (blue rain text on blue rain particles) is clearly diagnosed with a known fix direction.

The core challenge is not engineering complexity -- it is perceptual validation on physical LED hardware. LED displays have non-linear brightness curves, minimum brightness thresholds, and a different color gamut than LCD monitors. The prior v1.0 debug session proved that PNG previews on screen are insufficient for validating LED readability. All 8 weather animation types need systematic color tuning for vividness and inter-type distinguishability, followed by physical hardware UAT at 2+ meters in both bright and dim room conditions.

The secondary challenge is writing testable color-identity assertions. The existing test suite checks alpha thresholds (visibility gate) but not color identity (distinguishability gate). The new tests need to assert channel dominance properties (e.g., rain particles are blue-dominant) without being so brittle that they break on minor palette tweaks.

**Primary recommendation:** Coordinate particle and text colors as a unified palette -- tune all 8 animation types for vivid, saturated RGB values (changing RGB channels only, preserving alpha), change rain text to bright white `(255, 255, 255)` for maximum contrast against every animation, and add color-identity assertions that check channel dominance rather than exact RGB values.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Tune BOTH text colors and particle colors -- not just one side
- The 3D depth layering (far/near particles with text sandwiched) stays as-is
- User will verify every weather condition on the physical Pixoo 64 display personally
- Foreground particles still render over text -- preserve the depth effect
- Precipitation text shows number only (e.g. "1.5mm"), no label like "Regn"
- Precipitation text should ONLY appear when there's actual precipitation (>0mm) -- hide when dry
- This is a behavior change from current (always visible)
- Must be readable at 2+ meters in both well-lit and dim room conditions
- Brightness target: Claude's discretion (work across reasonable range)
- Review and tune ALL 8 weather animations, not just the broken rain one
- Current animations look "muddy" on the LED -- colors need more saturation/contrast
- The 2-layer depth system (far dim + near bright) works well and should be preserved
- Particles should feel more vivid and distinct from each other across weather types

### Claude's Discretion
- Overall text color palette structure (unified vs current split of yellow temp / teal hi-lo / blue rain)
- Specific rain text color choice (whatever contrasts best with all animation types)
- Whether to add text outlines/shadows for readability or rely on color alone
- Rain text positioning (keep current or move if it improves readability)
- Realistic vs stylized particle colors (balance realism with LED readability)
- Target brightness level for optimization
- Specific RGB values and alpha tuning for all 8 animation types

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FARGE-01 | Rain indicator text is visually distinct from rain animation particles on LED display | Rain text changes from blue `(50, 180, 255)` to white `(255, 255, 255)` for maximum contrast against all animation types. Rain particles become vivid blue with higher saturation. Color-identity tests assert rain particles are blue-dominant while text is white. |
| FARGE-02 | All 8 weather animation types verified for text/animation contrast | All 8 types need RGB-channel-only tuning for vividness and cross-type distinguishability. Per-animation color palettes documented below. Physical hardware UAT required as acceptance gate. |
| FARGE-03 | Color-identity regression tests prevent future color clashes | Tests assert channel-dominance properties (rain=blue-dominant, snow=white-ish, sun=yellow-dominant, etc.) plus a luminance contrast check between text colors and particle colors. Uses WCAG relative luminance formula. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | >=12.1.0 | RGBA image compositing, ImageDraw for particles/text | Already in use; only library needed for all rendering |
| pytest | (dev dep) | Color-identity regression tests | Already in use; test framework for existing 96 tests |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None needed | - | - | No new dependencies for this phase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual 1px text outline | Pillow stroke_width param | stroke_width does NOT work with BDF bitmap fonts -- only TrueType. Manual 4-cardinal-offset drawing is the only option. |
| External color-contrast library (wcag-contrast-ratio) | Inline luminance calculation | Inline is simpler for ~10 lines of math; no need for a PyPI dependency |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
No structural changes. All work stays within existing files:
```
src/display/
    layout.py            # COLOR_WEATHER_RAIN constant change + possibly new constants
    weather_anim.py      # Particle fill color RGB changes in all 6 animation classes
    renderer.py          # Precipitation text conditional display (>0mm only, number format)
tests/
    test_weather_anim.py # New color-identity assertions
```

### Pattern 1: Channel-Dominance Color Identity Testing
**What:** Assert that a color is "blue-dominant" by checking `B > R and B > G` with a minimum delta, rather than asserting exact RGB values.
**When to use:** Color-identity regression tests that need to survive minor palette tweaks while catching hue-family collisions.
**Example:**
```python
def assert_blue_dominant(r, g, b, min_delta=30):
    """Assert a color is perceptually blue (blue channel dominant)."""
    assert b > r + min_delta, f"Blue ({b}) not dominant over red ({r})"
    assert b > g + min_delta, f"Blue ({b}) not dominant over green ({g})"

def assert_white_ish(r, g, b, min_value=180, max_spread=40):
    """Assert a color is perceptually white (all channels high and close)."""
    assert r >= min_value, f"Red ({r}) too low for white"
    assert g >= min_value, f"Green ({g}) too low for white"
    assert b >= min_value, f"Blue ({b}) too low for white"
    spread = max(r, g, b) - min(r, g, b)
    assert spread <= max_spread, f"Channel spread ({spread}) too wide for white"
```

### Pattern 2: WCAG Relative Luminance for Contrast Verification
**What:** Calculate relative luminance per WCAG 2.0 formula, then compute contrast ratio between text and particle colors.
**When to use:** Asserting that text is readable against animation particles.
**Example:**
```python
def relative_luminance(r, g, b):
    """WCAG 2.0 relative luminance (0.0 to 1.0)."""
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

def contrast_ratio(color1, color2):
    """WCAG contrast ratio between two RGB tuples."""
    l1 = relative_luminance(*color1)
    l2 = relative_luminance(*color2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

# For LED displays at distance, aim for contrast ratio >= 3.0
# (lower than WCAG 4.5:1 because LED has high inherent contrast on black background)
```

### Pattern 3: Pixel Sampling for Animation Color Identity
**What:** Render several animation ticks, collect non-transparent pixel colors, compute the average or dominant RGB to verify animation identity.
**When to use:** Testing that animation particles maintain their intended color family across ticks.
**Example:**
```python
def sample_particle_colors(anim, num_ticks=5):
    """Sample all non-transparent pixel colors from multiple ticks."""
    colors = []
    for _ in range(num_ticks):
        bg, fg = anim.tick()
        for layer in (bg, fg):
            pixels = layer.load()
            for y in range(layer.height):
                for x in range(layer.width):
                    r, g, b, a = pixels[x, y]
                    if a > 0:
                        colors.append((r, g, b))
    return colors

def dominant_channel(colors):
    """Return which channel (R, G, B) dominates on average."""
    avg_r = sum(c[0] for c in colors) / len(colors)
    avg_g = sum(c[1] for c in colors) / len(colors)
    avg_b = sum(c[2] for c in colors) / len(colors)
    channels = {"R": avg_r, "G": avg_g, "B": avg_b}
    return max(channels, key=channels.get)
```

### Pattern 4: Manual Text Outline for BDF Bitmap Fonts
**What:** Since Pillow `stroke_width` does not work with BDF bitmap fonts, create a 1px outline by drawing the text 4 times at cardinal offsets (up/down/left/right) in a dark color, then drawing the actual text on top.
**When to use:** If color-alone proves insufficient for readability during hardware UAT. This is a Claude's Discretion item.
**Example:**
```python
def draw_outlined_text(draw, pos, text, font, fill, outline_fill=(0, 0, 0)):
    """Draw text with 1px outline using BDF bitmap font."""
    x, y = pos
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
    draw.text((x, y), text, font=font, fill=fill)
```
**Caveat:** On a 64px display with 4x6 or 5x8 fonts, a 1px outline adds 2px to the text footprint in each direction. This may cause adjacent text elements to overlap. Use sparingly -- only if color alone is insufficient.

### Anti-Patterns to Avoid
- **Adjusting alpha values alongside RGB changes:** Alpha ranges (bg: 40-100, fg: 90-200) were empirically tuned for LED visibility in v1.0. Changing both RGB and alpha simultaneously makes regressions impossible to isolate. **Change RGB only.**
- **Touching `_composite_layer()` in renderer.py:** The compositing pipeline was debugged and fixed in v1.0 (single-pass alpha_composite). It must not be modified in the same phase as color work.
- **Exact RGB value assertions in tests:** Tests like `assert color == (40, 90, 200)` break on any palette tweak. Use channel-dominance properties instead.
- **Validating colors on PNG previews only:** LED displays have non-linear brightness, minimum brightness thresholds, and different gamut. Physical hardware testing is the acceptance gate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color contrast calculation | Custom brightness formula | WCAG relative luminance formula | Well-standardized, accounts for human perception of R/G/B brightness differences |
| Text outlines on BDF fonts | Complex glyph manipulation | Simple 4-offset draw pattern | Proven pattern for pixel art; Pillow stroke_width doesn't work with bitmap fonts |
| Per-weather-condition text colors | Dynamic color picker system | Single bright white for all conditions | REQUIREMENTS.md explicitly marks per-weather text colors as out of scope; white contrasts with everything |

**Key insight:** The color problem is a palette coordination problem, not an algorithm problem. The fix is choosing the right RGB values for 6 animation types + 3 text colors and verifying them on hardware. No new architecture, libraries, or rendering changes are needed.

## Common Pitfalls

### Pitfall 1: New Color Collision After Fix
**What goes wrong:** Changing rain particles to vivid blue but keeping rain text blue creates the same indistinguishability in a different shade.
**Why it happens:** Treating particle and text colors independently rather than as a coordinated palette.
**How to avoid:** Choose particle and text colors as a unit. Recommended: rain text to white `(255, 255, 255)`, rain particles to vivid blue. White has maximum luminance contrast against every animation type's particle colors.
**Warning signs:** Text color's dominant channel matches any particle color's dominant channel.

### Pitfall 2: Muddy Colors on LED Despite Looking Good on Screen
**What goes wrong:** Colors selected by inspecting PNG debug frames look great on a monitor but appear washed out or indistinguishable on the physical Pixoo 64.
**Why it happens:** LCD/OLED monitors have much finer color gradation than 64x64 LED matrices. LEDs have minimum brightness thresholds (below ~RGB 15-20 per channel, LEDs stay dark). LED brightness is non-linear.
**How to avoid:** Use vivid, high-saturation colors. Favor primary/secondary colors (pure blue, pure white, warm yellow) over tertiary/muted tones. Always validate on physical hardware at 2+ meter viewing distance.
**Warning signs:** Any individual RGB channel value below 40 on particles meant to be visible.

### Pitfall 3: Snow and Rain Particles Look Identical
**What goes wrong:** Both rain and snow particles appear as "grey dots" on the LED (user's original complaint).
**Why it happens:** Both use low-saturation, similar-brightness colors. Snow `(200, 210, 230)` and rain `(40, 90, 200)` on a black LED background with alpha blending both read as dim grey-blue.
**How to avoid:** Maximize hue separation. Rain: saturated blue (high B, low R/G). Snow: bright near-white (all channels high, >220). The hue difference + brightness difference makes them distinguishable even at distance.
**Warning signs:** Average RGB values of rain and snow particles are within 40 of each other per channel.

### Pitfall 4: Thunder Inherits Rain Colors Automatically
**What goes wrong:** ThunderAnimation creates an internal `RainAnimation()` instance. Changes to RainAnimation particle colors automatically propagate to thunder. This is correct behavior but must be verified, not assumed.
**Why it happens:** `self._rain = RainAnimation(width, height)` in ThunderAnimation.__init__.
**How to avoid:** After changing rain colors, explicitly verify thunder animation samples contain the same rain particle colors. Include thunder in the color-identity test suite.
**Warning signs:** Thunder test passes but uses stale color expectations.

### Pitfall 5: Precipitation Text Behavior Change Breaks Tests
**What goes wrong:** Changing precipitation text from always-visible "Regn 1.5mm" to number-only "1.5mm" (hidden when dry) may break existing renderer tests that check for text pixels in the weather zone.
**Why it happens:** `test_rain_indicator_with_precipitation` in test_renderer.py checks for non-black pixels in the rain indicator area. The text content and positioning changes.
**How to avoid:** Update test expectations to match new behavior. Test both cases: precipitation > 0 shows "1.5mm", precipitation = 0 or None shows nothing.
**Warning signs:** Test failures in test_renderer.py after the behavior change.

### Pitfall 6: Negative Temperature Cyan Collides with Rain Particles
**What goes wrong:** `COLOR_WEATHER_TEMP_NEG = (80, 200, 255)` is cyan, which could visually blend with vivid blue rain particles during sub-zero rain conditions (sleet, cold rain).
**Why it happens:** Both cyan and blue are in the blue hue family; on an LED at distance, the distinction narrows.
**How to avoid:** Monitor during hardware testing. If collision is visible, shift negative temp color toward a distinct hue (e.g., lighter/more green-cyan). The prior research flagged this as a borderline case worth watching.
**Warning signs:** Cyan text disappears against blue rain particles when viewing at 2+ meters.

## Code Examples

Verified patterns from codebase inspection:

### Current Color Values (BEFORE fix)

```python
# layout.py -- text colors
COLOR_WEATHER_TEMP = (255, 200, 50)        # Bold warm yellow
COLOR_WEATHER_TEMP_NEG = (80, 200, 255)    # Vivid cyan-blue (negative temps)
COLOR_WEATHER_HILO = (120, 180, 160)       # Soft teal
COLOR_WEATHER_RAIN = (50, 180, 255)        # Vivid blue <-- PROBLEM: same hue as rain particles

# weather_anim.py -- particle colors (RGB only, alpha preserved)
# Rain far:  (40, 90, 200, 100)  <-- blue
# Rain near: (60, 140, 255, 200) <-- blue  <-- SAME HUE as rain text
# Snow far:  (200, 210, 230, 90) <-- grey-blue, looks like rain on LED
# Snow near: (255, 255, 255, 180) via _draw_crystal <-- white, good
# Cloud far: (140, 150, 160, 60)  <-- grey
# Cloud near: (180, 190, 200, 90) <-- grey
# Sun far:  (220, 180, 60) <-- warm yellow
# Sun near: (255, 230, 90) <-- warm yellow
# Fog far:  (160, 170, 180) <-- grey
# Fog near: (200, 210, 220) <-- grey
# Thunder: inherits Rain + (255, 255, 200) bolt + (255, 255, 180) flash
```

### Recommended Color Values (AFTER fix)

These are starting-point recommendations. Physical hardware testing is the acceptance gate.

```python
# layout.py -- text colors (new)
COLOR_WEATHER_TEMP = (255, 220, 50)        # Keep warm yellow (already works well)
COLOR_WEATHER_TEMP_NEG = (80, 200, 255)    # Keep cyan (monitor for rain collision)
COLOR_WEATHER_HILO = (120, 200, 160)       # Slightly more green-teal for vibrancy
COLOR_WEATHER_RAIN = (255, 255, 255)       # CHANGE: white for max contrast against ALL animations

# weather_anim.py -- particle colors (change RGB, KEEP ALPHA UNCHANGED)
# Rain far:  (30, 80, 220, 100)   -- more saturated blue (lower R, raise B)
# Rain near: (50, 120, 255, 200)  -- vivid blue (lower R, keep B high)
# Snow far:  (220, 230, 255, 90)  -- cool white, not grey (raise all channels)
# Snow near: keep (255, 255, 255, 180) -- already white, good
# Cloud far: (150, 160, 180, 60)  -- slightly more blue-grey
# Cloud near: (190, 200, 220, 90) -- slightly more blue-grey
# Sun far:  (240, 200, 40)        -- more vivid warm yellow (raise R, lower B)
# Sun near: (255, 240, 60)        -- bright warm yellow
# Fog far:  (180, 190, 200)       -- slightly brighter grey
# Fog near: (210, 220, 235)       -- slightly brighter blue-grey
# Thunder bolt: (255, 255, 220)   -- keep warm white bolt
# Thunder flash: (255, 255, 200)  -- keep warm flash
```

### Precipitation Text Conditional Display (renderer.py)

```python
# CURRENT (in render_weather_zone):
if state.weather_precip_mm is not None and state.weather_precip_mm > 0:
    rain_text = f"Regn {state.weather_precip_mm:.1f}"
    # ... draw

# NEW behavior:
if state.weather_precip_mm is not None and state.weather_precip_mm > 0:
    rain_text = f"{state.weather_precip_mm:.1f}mm"
    # ... draw with COLOR_WEATHER_RAIN (now white)
# No else -- when precip is 0 or None, show nothing
```

Note: Examining the actual current renderer code, it already only shows rain text when `weather_precip_mm is not None and weather_precip_mm > 0`. The current format is `f"{state.weather_precip_mm:.1f}mm"`. So the behavior is already partially correct. The main changes are:
1. Verify no "Regn" label exists (it was already removed in v1.0 based on code inspection)
2. The `COLOR_WEATHER_RAIN` constant change is the key text color fix

### Color-Identity Test Pattern

```python
class TestColorIdentity:
    """Verify particle colors match their weather condition identity."""

    def _sample_particle_rgb(self, anim, num_ticks=5):
        """Collect all non-transparent pixel RGB values from multiple ticks."""
        colors = []
        for _ in range(num_ticks):
            bg, fg = anim.tick()
            for layer in (bg, fg):
                pixels = layer.load()
                for y in range(layer.height):
                    for x in range(layer.width):
                        r, g, b, a = pixels[x, y]
                        if a > 0:
                            colors.append((r, g, b))
        return colors

    def test_rain_particles_are_blue_dominant(self):
        anim = RainAnimation()
        colors = self._sample_particle_rgb(anim)
        assert len(colors) > 0
        avg_r = sum(c[0] for c in colors) / len(colors)
        avg_g = sum(c[1] for c in colors) / len(colors)
        avg_b = sum(c[2] for c in colors) / len(colors)
        assert avg_b > avg_r + 20, f"Rain not blue-dominant: R={avg_r:.0f} G={avg_g:.0f} B={avg_b:.0f}"
        assert avg_b > avg_g + 20, f"Rain not blue-dominant: R={avg_r:.0f} G={avg_g:.0f} B={avg_b:.0f}"

    def test_snow_particles_are_white_ish(self):
        anim = SnowAnimation()
        colors = self._sample_particle_rgb(anim)
        assert len(colors) > 0
        avg_r = sum(c[0] for c in colors) / len(colors)
        avg_g = sum(c[1] for c in colors) / len(colors)
        avg_b = sum(c[2] for c in colors) / len(colors)
        min_val = min(avg_r, avg_g, avg_b)
        assert min_val >= 180, f"Snow not white-ish: R={avg_r:.0f} G={avg_g:.0f} B={avg_b:.0f}"

    def test_sun_particles_are_yellow_dominant(self):
        anim = SunAnimation()
        colors = self._sample_particle_rgb(anim)
        assert len(colors) > 0
        avg_r = sum(c[0] for c in colors) / len(colors)
        avg_g = sum(c[1] for c in colors) / len(colors)
        avg_b = sum(c[2] for c in colors) / len(colors)
        # Yellow = high R + high G, low B
        assert avg_r > avg_b + 50, f"Sun R not dominant over B: R={avg_r:.0f} B={avg_b:.0f}"
        assert avg_g > avg_b + 30, f"Sun G not dominant over B: G={avg_g:.0f} B={avg_b:.0f}"

    def test_rain_text_contrasts_with_rain_particles(self):
        """Rain text color must have sufficient contrast against rain particle colors."""
        from src.display.layout import COLOR_WEATHER_RAIN
        # Sample rain particle average color
        anim = RainAnimation()
        colors = self._sample_particle_rgb(anim)
        avg_particle = (
            sum(c[0] for c in colors) / len(colors),
            sum(c[1] for c in colors) / len(colors),
            sum(c[2] for c in colors) / len(colors),
        )
        ratio = contrast_ratio(COLOR_WEATHER_RAIN, avg_particle)
        assert ratio >= 2.5, f"Rain text/particle contrast ratio {ratio:.1f} too low (need >= 2.5)"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Double-alpha compositing (invisible animation) | Single-pass alpha_composite | v1.0 Phase 3 Plan 3 | Animations now visible on LED hardware |
| 1px rain/snow particles | Multi-pixel particles (1x2 rain, 3x3+ snow crystal) | v1.0 Phase 3 Plan 3 | Particles distinguishable at viewing distance |
| Alpha-only visibility tests | Alpha + pixel-coverage tests | v1.0 Phase 3 Plan 3 | Regression gate for animation visibility |
| No color-identity tests | (Phase 7 will add) | Pending | Will prevent future color collision regressions |

**Deprecated/outdated:**
- Pillow `stroke_width` for BDF font outlines -- does not work; use manual 4-offset draw pattern if outlines needed

## Open Questions

1. **Rain text: white vs orange?**
   - What we know: Prior research recommends white `(255, 255, 255)` for maximum contrast. Alternative is orange `(255, 140, 60)` which has good contrast but adds another warm color near the yellow temperature text.
   - What's unclear: Which looks better on the physical LED at 2+ meters.
   - Recommendation: Start with white (highest contrast, simplest). Fall back to orange only if white creates visual confusion with snow particles. User decision during hardware UAT.

2. **Negative temperature cyan vs rain particle blue -- visible collision?**
   - What we know: `COLOR_WEATHER_TEMP_NEG = (80, 200, 255)` is cyan. Rain particles will become vivid blue `(50, 120, 255)`. Both are blue-family.
   - What's unclear: Whether they're distinguishable at 2+ meters on the LED during sub-zero rain weather.
   - Recommendation: Monitor during hardware UAT. Fix only if collision is visible. Potential fix: shift cyan toward green `(60, 220, 200)`.

3. **Text outlines: needed or not?**
   - What we know: Pillow `stroke_width` does not work with BDF fonts. Manual 4-offset outline is possible but adds 2px to text footprint. On 64px display with 4x6 font, this is significant.
   - What's unclear: Whether color-alone provides sufficient readability with foreground particles overlapping text.
   - Recommendation: Try color-only first (simpler, no footprint increase). Add outlines only if hardware UAT shows readability problems. The foreground particle alpha (90-200) means text occlusion is partial, not total.

4. **Snow far-flake color: grey-blue or cool white?**
   - What we know: Current `(200, 210, 230, 90)` reads as grey on LED, indistinguishable from rain at a glance. Recommended `(220, 230, 255, 90)` is brighter and whiter.
   - What's unclear: Exact threshold where it becomes distinct from rain on hardware.
   - Recommendation: Use `(220, 230, 255)` as starting point. The near flakes are already pure white `(255, 255, 255)` which provides the primary snow identity.

## Sources

### Primary (HIGH confidence)
- Codebase audit: `src/display/weather_anim.py` -- all 6 animation classes with exact fill colors and alpha values
- Codebase audit: `src/display/layout.py` -- all COLOR_WEATHER_* constants with exact RGB values
- Codebase audit: `src/display/renderer.py` -- compositing pipeline, text rendering, precipitation display logic
- Codebase audit: `tests/test_weather_anim.py` -- existing alpha/visibility regression tests
- `.planning/debug/weather-animation-too-subtle.md` -- documented compositing bug diagnosis and fix
- `.planning/todos/done/2026-02-20-weather-animation-and-rain-text-colors-indistinguishable.md` -- user-reported bug
- `.planning/research/SUMMARY.md` -- prior v1.1 research with color recommendations and pitfalls
- `.planning/STATE.md` -- constraint: "Change RGB channels only; do not adjust alpha values"
- [Pillow ImageDraw docs](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) -- stroke_width only works with TrueType fonts, not BDF bitmap
- [WCAG 2.0 Relative Luminance](https://www.w3.org/WAI/GL/wiki/Relative_luminance) -- luminance formula for contrast ratio calculation

### Secondary (MEDIUM confidence)
- [LED readability best practices](https://www.szlightall.com/a-news-how-to-optimize-led-screen-content-for-readability.html) -- favor bright, saturated colors; high contrast text-vs-background
- [LED content design](https://nummax.com/en/nouvelle/how-to-create-effective-content-for-your-nummax-led-display-part-2-3/) -- avoid animated backgrounds behind text when possible; keep text areas clean
- [Color Theory for Pixel Artists](https://pixelparmesan.com/blog/color-theory-for-pixel-artists-its-all-relative) -- saturation and hue separation principles for pixel art
- [WCAG contrast ratio technique](https://www.w3.org/TR/WCAG20-TECHS/G17.html) -- contrast ratio >= 4.5:1 for normal text, >= 3:1 for large text

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all work in existing Pillow/pytest stack
- Architecture: HIGH -- all 6 animation classes, compositing pipeline, and test patterns directly audited from source code
- Pitfalls: HIGH -- derived from documented v1.0 debug sessions, actual user bug reports, and codebase-specific constraints (alpha preservation, BDF font limitations)
- Color recommendations: MEDIUM -- RGB values are educated starting points based on color theory and prior research, but physical hardware validation is the true acceptance gate

**Research date:** 2026-02-21
**Valid until:** Indefinite -- color theory and Pillow API are stable; codebase-specific findings valid until architecture changes
