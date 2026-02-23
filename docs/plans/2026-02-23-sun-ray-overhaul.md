# Sun Ray Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace random sky-wide sun rays with radial beams that emit outward from a half-sun at the top-right of the weather zone.

**Architecture:** Rewrite `SunAnimation` in `weather_anim.py` — new half-sun body drawn as a semicircle clipped at y=0, rays stored as polar (angle, distance) instead of cartesian (x, y), alpha fades with distance. Update tests to match new geometry.

**Tech Stack:** Python, Pillow (PIL), pytest

---

### Task 1: Update sun body tests for new position and size

**Files:**
- Modify: `tests/test_weather_anim.py:603-632`

**Step 1: Write the updated tests**

Replace the `TestSunBody` class with tests for the new half-sun geometry:

```python
class TestSunBody:
    """Verify half-sun body is visible at top-right of weather zone."""

    def test_sun_body_produces_warm_pixels_at_position(self):
        """Sun body should produce warm yellow pixels near its position."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        # Half-sun center at (_SUN_X, _SUN_Y) with lower hemisphere visible
        sx, sy = SunAnimation._SUN_X, SunAnimation._SUN_Y
        # Check a pixel just below center (in the visible lower half)
        check_y = min(sy + 2, 23)
        pixel = bg.getpixel((sx, check_y))
        r, g, b, a = pixel
        assert a >= 150, f"Sun body alpha {a} too low at ({sx}, {check_y})"
        assert r > b + 50, f"Sun body not warm yellow: R={r} B={b}"

    def test_sun_body_has_glow(self):
        """Sun body should have a softer glow around the core."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        sx, sy = SunAnimation._SUN_X, SunAnimation._SUN_Y
        r = SunAnimation._SUN_RADIUS
        # Check a pixel at the edge of the glow, below center (visible half)
        glow_y = min(sy + r + 1, 23)
        glow_pixel = bg.getpixel((sx, glow_y))
        _, _, _, a = glow_pixel
        assert a > 0, "No glow detected around sun body"

    def test_sun_animation_still_has_rays(self):
        """Sun animation should still produce ray particles alongside the body."""
        anim = SunAnimation()
        colors = _sample_particle_rgb(anim, num_ticks=3)
        assert len(colors) > 10, f"Only {len(colors)} particles -- rays should still be active"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_weather_anim.py::TestSunBody -v`
Expected: FAIL — old sun body position doesn't match new assertions (check_y pixel may miss the old tiny sun).

**Step 3: Commit**

```bash
git add tests/test_weather_anim.py
git commit -m "test: update sun body tests for half-sun geometry"
```

---

### Task 2: Add test for radial ray origin

**Files:**
- Modify: `tests/test_weather_anim.py`

**Step 1: Write a test that rays originate near the sun**

Add a new test class after `TestSunBody`:

```python
class TestSunRayOrigin:
    """Verify sun rays emanate from the sun position, not randomly."""

    def test_rays_cluster_near_sun(self):
        """First-tick rays should be near the sun, not scattered randomly."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        sx, sy = SunAnimation._SUN_X, SunAnimation._SUN_Y

        # Count non-transparent pixels in a box around the sun vs far away
        near_sun = 0
        far_from_sun = 0
        for layer in (bg, fg):
            for y in range(24):
                for x in range(64):
                    _, _, _, a = layer.getpixel((x, y))
                    if a > 0:
                        dist = math.sqrt((x - sx) ** 2 + (y - sy) ** 2)
                        if dist <= 15:
                            near_sun += 1
                        else:
                            far_from_sun += 1

        # Most lit pixels should be near the sun on first tick
        total = near_sun + far_from_sun
        assert total > 0, "No visible pixels at all"
        near_ratio = near_sun / total
        assert near_ratio >= 0.3, (
            f"Only {near_ratio:.0%} of pixels near sun -- rays should originate from sun"
        )
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_weather_anim.py::TestSunRayOrigin -v`
Expected: FAIL — current rays spawn randomly, so near_ratio will be low.

**Step 3: Commit**

```bash
git add tests/test_weather_anim.py
git commit -m "test: add ray origin clustering test"
```

---

### Task 3: Rewrite SunAnimation with half-sun and radial rays

**Files:**
- Modify: `src/display/weather_anim.py:276-368`

**Step 1: Replace the SunAnimation class**

Replace lines 276-368 with:

```python
class SunAnimation(WeatherAnimation):
    """Half-sun at top-right with rays beaming outward radially.

    A semicircle (lower half) is drawn clipped at the top edge of the
    weather zone.  Rays emit from the sun center and travel outward,
    fading with distance.

    Far rays (behind): dimmer, thinner, slower.
    Near rays (in front): brighter, longer, faster -- beaming over text.
    """

    _SUN_X = 48
    _SUN_Y = 0
    _SUN_RADIUS = 7

    # Max distance a ray can travel before respawning
    _MAX_DIST = 28

    def __init__(self, width: int = 64, height: int = 24) -> None:
        super().__init__(width, height)
        self.far_rays: list[list[float]] = []
        self.near_rays: list[list[float]] = []
        self._spawn_far(9)
        self._spawn_near(5)

    def _random_angle(self) -> float:
        """Return a random angle in the downward-facing semicircle (0 to pi)."""
        return random.uniform(0.05 * math.pi, 0.95 * math.pi)

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_rays.append([
                self._random_angle(),             # angle (radians)
                random.uniform(0, self._MAX_DIST), # distance (staggered start)
                random.uniform(0.4, 0.8),          # speed
                random.randint(2, 4),              # length (pixels)
                random.randint(100, 140),          # base alpha
            ])

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_rays.append([
                self._random_angle(),
                random.uniform(0, self._MAX_DIST),
                random.uniform(0.8, 1.6),
                random.randint(4, 7),
                random.randint(160, 220),
            ])

    def _respawn_ray(self, ray: list[float], near: bool) -> None:
        """Reset a ray to the sun with new random angle."""
        ray[0] = self._random_angle()
        ray[1] = 0.0
        if near:
            ray[2] = random.uniform(0.8, 1.6)
            ray[3] = random.randint(4, 7)
            ray[4] = random.randint(160, 220)
        else:
            ray[2] = random.uniform(0.4, 0.8)
            ray[3] = random.randint(2, 4)
            ray[4] = random.randint(100, 140)

    def _draw_ray(self, draw: ImageDraw.Draw, ray: list[float], color: tuple) -> None:
        angle, dist, speed, length, base_alpha = (
            ray[0], ray[1], ray[2], int(ray[3]), ray[4],
        )
        # Ray start position (polar to cartesian from sun center)
        x1 = self._SUN_X + dist * math.cos(angle)
        y1 = self._SUN_Y + dist * math.sin(angle)
        # Ray end position (extends further along the same angle)
        x2 = self._SUN_X + (dist + length) * math.cos(angle)
        y2 = self._SUN_Y + (dist + length) * math.sin(angle)

        # Alpha fades with distance from sun
        fade = max(0.0, 1.0 - dist / self._MAX_DIST)
        alpha = int(base_alpha * fade)

        ix1, iy1 = int(x1), int(y1)
        ix2, iy2 = int(x2), int(y2)

        # Only draw if at least part of the ray is within the zone
        if (0 <= ix1 < self.width or 0 <= ix2 < self.width) and \
           (0 <= iy1 < self.height or 0 <= iy2 < self.height) and alpha > 5:
            draw.line(
                [
                    (max(0, min(ix1, self.width - 1)), max(0, min(iy1, self.height - 1))),
                    (max(0, min(ix2, self.width - 1)), max(0, min(iy2, self.height - 1))),
                ],
                fill=(*color, alpha),
            )

        # Advance ray outward
        ray[1] += speed

    def _recycle_rays(self, rays: list[list[float]], near: bool) -> None:
        """Respawn rays that have traveled past max distance or exited zone."""
        for ray in rays:
            if ray[1] >= self._MAX_DIST:
                self._respawn_ray(ray, near)

    def _draw_sun_body(self, draw: ImageDraw.Draw) -> None:
        """Draw a warm half-sun semicircle clipped at the top of the zone."""
        sx, sy, r = self._SUN_X, self._SUN_Y, self._SUN_RADIUS
        # Outer glow (larger, dimmer)
        draw.ellipse(
            [sx - r - 2, sy - r - 2, sx + r + 2, sy + r + 2],
            fill=(255, 200, 40, 80),
        )
        # Sun body (bright warm yellow)
        draw.ellipse(
            [sx - r, sy - r, sx + r, sy + r],
            fill=(255, 220, 60, 200),
        )
        # The top half of the ellipse is above y=0 and naturally clipped
        # by the RGBA image bounds, producing a semicircle effect.

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Sun body behind text
        self._draw_sun_body(bg_draw)

        for ray in self.far_rays:
            self._draw_ray(bg_draw, ray, (240, 200, 40))
        self._recycle_rays(self.far_rays, near=False)

        for ray in self.near_rays:
            self._draw_ray(fg_draw, ray, (255, 240, 60))
        self._recycle_rays(self.near_rays, near=True)

        return bg, fg

    def reset(self) -> None:
        self.far_rays.clear()
        self.near_rays.clear()
        self._spawn_far(9)
        self._spawn_near(5)
```

**Step 2: Run all sun-related tests**

Run: `python -m pytest tests/test_weather_anim.py::TestSunBody tests/test_weather_anim.py::TestSunRayOrigin tests/test_weather_anim.py::TestColorIdentity::test_sun_particles_are_yellow_dominant tests/test_weather_anim.py::TestAnimationVisibility::test_sun_alpha_above_minimum -v`
Expected: ALL PASS

**Step 3: Run the full test suite**

Run: `python -m pytest tests/test_weather_anim.py -v`
Expected: ALL PASS — no regressions in other animations.

**Step 4: Commit**

```bash
git add src/display/weather_anim.py
git commit -m "feat: overhaul sun rays to emit radially from half-sun body"
```

---

### Task 4: Run full test suite and verify visually

**Files:** None (verification only)

**Step 1: Run the complete test suite**

Run: `python -m pytest -v`
Expected: ALL PASS

**Step 2: Commit (if any fixups needed)**

Only if adjustments were made in previous steps.
