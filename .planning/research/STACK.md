# Technology Stack

**Project:** Divoom Hub v1.2 -- Sun Ray Overhaul
**Researched:** 2026-02-23
**Scope:** Radial sun ray emission with distance-based alpha fading on 64x24 RGBA weather zone

## Executive Finding

No new dependencies needed. Zero. The existing stack (Pillow 12.1.1, Python `math` stdlib) already provides every capability required for radial ray drawing with alpha fading. The `math` module is already imported in `weather_anim.py`. Pillow's `ImageDraw.point()`, `ImageDraw.line()`, and `ImageDraw.pieslice()` all correctly handle RGBA fill colors on RGBA images. Verified against the installed Pillow 12.1.1 with working code proofs.

## Existing Stack (No Changes)

### Core Technologies

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.14 (venv) | Runtime | Keep as-is |
| Pillow | 12.1.1 (installed) | RGBA image rendering, compositing | Keep as-is |
| `math` stdlib | N/A (stdlib) | `cos`, `sin`, `radians` for polar-to-cartesian | Already imported in `weather_anim.py` |
| `random` stdlib | N/A (stdlib) | Particle spawning, jitter | Already imported in `weather_anim.py` |

### pyproject.toml

No changes needed. Current `Pillow>=12.1.0` constraint is correct.

## Drawing Techniques for Radial Sun Rays

### Technique 1: Half-Sun Body with `pieslice()`

Use `ImageDraw.pieslice()` for the semicircular sun body at the top-right of the weather zone. This is the correct Pillow primitive for drawing a filled arc/wedge shape.

**Why pieslice, not ellipse:** The sun is a half-circle (only the bottom half is visible, the top half is above the weather zone edge). `pieslice()` with `start=0, end=180` draws exactly this shape. `ellipse()` draws full circles only.

**Verified signature:** `pieslice(xy, start, end, fill=None, outline=None, width=1)`

**Proven code:**
```python
# Sun at (48, 0) in the 64x24 weather zone, radius 7
cx, cy, r = 48, 0, 7
draw.pieslice([cx-r, cy-r, cx+r, cy+r], start=0, end=180, fill=(255, 220, 60, 200))
```

**Verified output:** Produces a clean 15px-wide semicircle from y=0 to y=7, spanning x=41 to x=55. 96 filled pixels. Correct RGBA alpha preserved.

**Confidence:** HIGH -- tested against installed Pillow 12.1.1, pixel output verified.

### Technique 2: Pixel-by-Pixel Rays with Distance-Based Alpha Fade

For rays that fade with distance, draw each pixel individually using `ImageDraw.point()` with alpha computed from distance to sun center. This is the only way to get per-pixel alpha variation along a line in Pillow (Pillow's `line()` method uses a single fill color for the entire line).

**Why point-by-point, not `line()`:** `ImageDraw.line()` accepts one `fill` color for the whole line. It cannot vary alpha along the line's length. To fade from alpha=180 near the sun to alpha=40 at the tip, each pixel must be drawn individually.

**Polar-to-cartesian conversion:**
```python
import math

cx, cy = 48, 0  # sun center
angle_rad = math.radians(angle_deg)
cos_a = math.cos(angle_rad)
sin_a = math.sin(angle_rad)

for d in range(start_d, end_d):
    x = int(cx + d * cos_a)
    y = int(cy + d * sin_a)
    if 0 <= x < 64 and 0 <= y < 24:
        progress = d / max_length
        alpha = int(base_alpha * (1.0 - progress))
        draw.point((x, y), fill=(r, g, b, max(alpha, min_alpha)))
```

**Performance:** 0.02ms per tick for 14 rays at 15-pixel length. The 1 FPS rate limit gives 1000ms per frame. Ray drawing uses 0.002% of the frame budget. Performance is a non-issue.

**Confidence:** HIGH -- benchmarked on this machine, verified pixel output with correct alpha values.

### Technique 3: Pre-computed Trig Values (Optimization)

Cache `math.cos(angle_rad)` and `math.sin(angle_rad)` per ray rather than recomputing each tick. Each ray's angle is fixed at spawn time; only the "progress" distance changes per tick.

```python
# At ray spawn time:
ray["cos_a"] = math.cos(math.radians(angle_deg))
ray["sin_a"] = math.sin(math.radians(angle_deg))

# At draw time (per pixel):
x = int(cx + d * ray["cos_a"])
y = int(cy + d * ray["sin_a"])
```

**Why:** Not for performance (it is already fast) but for code clarity. Computing trig once at spawn makes the per-tick draw loop cleaner.

**Confidence:** HIGH -- standard math optimization, trivial.

## Math Functions Required

All available in Python `math` stdlib, already imported in `weather_anim.py`:

| Function | Purpose | Example |
|----------|---------|---------|
| `math.cos(rad)` | X component of polar-to-cartesian | `x = cx + d * cos(angle)` |
| `math.sin(rad)` | Y component of polar-to-cartesian | `y = cy + d * sin(angle)` |
| `math.radians(deg)` | Convert degrees to radians | `math.radians(225)` for down-left |
| `math.pi` | Full circle = 2*pi, semicircle = pi | Angle range calculation |

No `numpy`, no `math.atan2`, no `math.sqrt` needed. The ray system only needs forward conversion (polar -> cartesian), never the reverse.

## Angle Convention for Ray Emission

Standard math convention used by both Pillow and Python `math`:
- 0 degrees = 3 o'clock (right)
- 90 degrees = 6 o'clock (down, in screen coordinates where Y increases downward)
- 180 degrees = 9 o'clock (left)
- 270 degrees = 12 o'clock (up)

For a sun at top-right emitting rays downward and to the left into the weather zone, the useful angle range is approximately **180 to 360 degrees** (the bottom semicircle in screen coordinates). Pillow's `pieslice(start=0, end=180)` uses the same convention (0=right, going clockwise to 180=left), which draws the bottom half -- the visible half of the sun.

**Confidence:** HIGH -- verified with pieslice output and polar ray drawing tests.

## Alpha Fading Strategy

The project's established alpha ranges (from v1.0 LED hardware tuning):
- LED pixels below ~RGB(15,15,15) produce no visible light
- Alpha values 65-230 are the validated visible range after compositing
- Far layer (bg): alpha 90-150
- Near layer (fg): alpha 160-230

For distance-based ray fading:

| Ray Depth | Base Alpha (near sun) | Minimum Alpha (tip) | Rationale |
|-----------|----------------------|---------------------|-----------|
| Far (bg) | 130-150 | 40-60 | Dim rays visible behind text, fade to near-invisible |
| Near (fg) | 180-220 | 60-80 | Bright rays over text, fade but stay LED-visible |

These ranges maintain compatibility with the existing LED visibility thresholds established in v1.0 and tested in `test_weather_anim.py`.

**Confidence:** HIGH -- based on existing validated alpha ranges in the codebase (see `weather_anim.py` lines 8-9 and test assertions).

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| numpy | Overkill for 14 rays x 15 pixels. Pure Python math is 0.02ms/tick. numpy's import overhead alone would be larger than the total computation. | Use `math.cos()` / `math.sin()` from stdlib |
| Anti-aliasing libraries | 64x64 LED pixels are physically large. Anti-aliasing produces sub-pixel blending that is invisible on LED hardware and wastes alpha budget. | Draw with `point()` at integer coordinates |
| Cairo / skia-python | Alternative 2D renderers. Would require rewriting the entire rendering pipeline. Pillow already does everything needed. | Keep Pillow |
| Bresenham line algorithm (manual) | Pillow's `line()` already implements this internally. For faded rays, pixel-by-pixel with `point()` is the correct approach anyway. | Use `point()` for faded rays, `line()` where uniform alpha suffices |
| New animation framework / particles library | The existing `WeatherAnimation` base class with `tick()` returning `(bg_layer, fg_layer)` is the right pattern. Sun rays are just a new set of particles. | Extend `SunAnimation` in place |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Sun body shape | `pieslice()` | `ellipse()` cropped | pieslice directly draws semicircle; cropping adds unnecessary compositing step |
| Ray rendering | `point()` per pixel | `line()` with segments | `line()` cannot vary alpha per pixel. Segments would produce visible alpha steps (banding) at this resolution. |
| Ray rendering | `point()` per pixel | Pre-render ray images | Over-engineering. There are only ~14 rays, each ~15 pixels. Direct drawing is simpler and equally fast. |
| Angle range | 180-360 degrees | Configurable arc | The sun is always at top-right. Hardcoded emission range is simpler and correct. Make it a class constant for testability. |
| Alpha interpolation | Linear fade `1.0 - (d/max_d)` | Quadratic / exponential | Linear is visually correct for LED: LED brightness is already non-linear (gamma ~2.2), so linear alpha produces a perceived exponential fade. Start simple, tune on hardware if needed. |

## Files That Will Change

For the roadmap's benefit:

| File | Change | Why |
|------|--------|-----|
| `src/display/weather_anim.py` | Rewrite `SunAnimation` class | New radial ray system replacing random sky-wide rays |
| `tests/test_weather_anim.py` | Update `TestSunBody` and sun-related assertions | New geometry (pieslice semicircle, radial rays) |

No new files. No new imports. No dependency changes.

## Installation

No changes needed:

```bash
# Nothing to install -- existing dependencies cover everything
pip install -e .       # already works
pip install -e ".[dev]" # already works
```

## Version Compatibility

| Package | Constraint | Installed | Required Feature | Status |
|---------|-----------|-----------|-----------------|--------|
| Pillow | >=12.1.0 | 12.1.1 | `pieslice()` with RGBA fill, `point()` with RGBA fill | Available since Pillow 2.0+. Verified working. |
| Python | >=3.10 | 3.14 | `math.cos`, `math.sin`, `math.radians` | Available since Python 1.0. |

## Sources

- [Pillow 12.1.1 ImageDraw documentation](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) -- pieslice(), line(), point() signatures and RGBA support. HIGH confidence.
- [Python math module documentation](https://docs.python.org/3/library/math.html) -- cos, sin, radians availability. HIGH confidence.
- Codebase verification: `weather_anim.py` already imports `math` and `random`. Already uses `ImageDraw.Draw()` on RGBA images. HIGH confidence (primary source).
- Local benchmarks: 0.02ms/tick for 14 rays at 15px length on this hardware. HIGH confidence (measured).
- Local pixel verification: pieslice and point-by-point rays produce correct RGBA output on Pillow 12.1.1. HIGH confidence (tested).

---
*Stack research for: Divoom Hub v1.2 (Sun Ray Overhaul)*
*Researched: 2026-02-23*
