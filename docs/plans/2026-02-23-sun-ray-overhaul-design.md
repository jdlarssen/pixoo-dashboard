# Sun Ray Animation Overhaul

## Problem

Sun rays spawn randomly across the entire 64x24 weather zone with no spatial
connection to the sun body. On a sunny day the beams appear to come from the
sky rather than from the sun.

## Design

### Sun Body

- Half-sun semicircle at **(x=48, y=0)** in the weather zone (top-right of
  the bottom section on the 64x64 display).
- **Radius 7** — only the lower hemisphere renders, producing a ~14px-wide,
  ~7px-tall arc clipped at the top edge.
- Two-layer glow preserved: outer glow (dimmer, larger) + inner body (bright
  warm yellow).

### Rays — Radial Emission

- Rays **spawn at the sun position** and shoot **outward** along random angles
  within a downward-facing ~180-degree fan.
- Each ray stores: angle, speed, distance-from-sun, length, alpha.
- Each tick the ray moves outward along its angle. **Alpha fades** as distance
  from the sun increases.
- When a ray fades out or exits the zone it respawns at the sun with a new
  random angle.
- Initial rays are staggered at varying distances so the animation starts as a
  continuous effect, not a burst.

### Depth Layers

- **Far rays (bg layer):** 9 rays, slower, shorter, dimmer — behind text.
- **Near rays (fg layer):** 5 rays, faster, longer, brighter — over text.
- Color scheme unchanged: far = (240, 200, 40), near = (255, 240, 60).

### Tests

- Update `TestSunBody` assertions for the new position and radius.
- Existing alpha, color-identity, and ray-presence tests remain valid with
  minor coordinate adjustments.
