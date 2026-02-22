"""Animated weather overlays for the 64x24 weather zone with depth layers.

Each animation produces two RGBA layers:
- bg_layer: rendered BEHIND text (far/dim particles for depth)
- fg_layer: rendered IN FRONT of text (near/bright particles for 3D effect)

Alpha values tuned for LED hardware visibility (90-230 range).
LED pixels below ~RGB(15,15,15) produce no visible light, so alpha values
must be high enough that the composited result exceeds this threshold.

Color palette: vivid, LED-friendly colors per weather type.
Rain=blue, snow=bright white, sun=warm yellow, fog=soft white, clouds=grey-white.
Night clear=twinkling white/blue stars with organic per-star randomness.
"""

import random

from PIL import Image, ImageDraw


class WeatherAnimation:
    """Base class for weather zone animations with depth layers.

    Produces two 64x24 RGBA overlay images per tick:
    - bg_layer: composited before text (behind)
    - fg_layer: composited after text (in front)
    """

    def __init__(self, width: int = 64, height: int = 24) -> None:
        self.width = width
        self.height = height

    def _empty(self) -> Image.Image:
        return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def tick(self) -> tuple[Image.Image, Image.Image]:
        """Return (bg_layer, fg_layer) as RGBA images."""
        return self._empty(), self._empty()

    def reset(self) -> None:
        """Reset animation state to initial conditions."""


class RainAnimation(WeatherAnimation):
    """Falling blue raindrops at two depths with intensity scaling.

    Far drops (behind text): dimmer, shorter, slower.
    Near drops (in front of text): brighter, longer, faster.

    Particle count scales with precipitation_mm:
    - Light (< 1mm): sparse drizzle (8 far, 4 near)
    - Moderate (1-3mm): normal rain (14 far, 8 near)
    - Heavy (> 3mm): dense downpour (22 far, 14 near)
    """

    def __init__(self, width: int = 64, height: int = 24, precipitation_mm: float = 2.0) -> None:
        super().__init__(width, height)
        self.precipitation_mm = precipitation_mm
        self._far_count, self._near_count = self._particle_counts(precipitation_mm)
        self.far_drops: list[list[int]] = []
        self.near_drops: list[list[int]] = []
        self._spawn_far(self._far_count)
        self._spawn_near(self._near_count)

    @staticmethod
    def _particle_counts(precipitation_mm: float) -> tuple[int, int]:
        """Return (far_count, near_count) based on precipitation intensity."""
        if precipitation_mm < 1.0:
            return 8, 4
        elif precipitation_mm <= 3.0:
            return 14, 8
        elif precipitation_mm <= 5.0:
            return 22, 14
        else:
            return 30, 18

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_drops.append([
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ])

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_drops.append([
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ])

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Far drops -- behind text, dimmer, 2px streak
        for drop in self.far_drops:
            x, y = drop[0], drop[1]
            if 0 <= x < self.width and 0 <= y < self.height:
                bg_draw.line([(x, y), (x, min(y + 1, self.height - 1))], fill=(30, 80, 220, 140))
            drop[1] += 1
            drop[0] += random.choice([-1, 0, 0, 0])
            if drop[1] >= self.height:
                drop[1] = 0
                drop[0] = random.randint(0, self.width - 1)

        # Near drops -- in front of text, brighter, 3px streak, faster
        # Heavy rain (>3mm) falls faster with longer streaks
        heavy = self.precipitation_mm > 3.0
        for drop in self.near_drops:
            x, y = drop[0], drop[1]
            streak = 3 if heavy else 2
            if 0 <= x < self.width and 0 <= y < self.height:
                fg_draw.line([(x, y), (x, min(y + streak, self.height - 1))], fill=(50, 120, 255, 230))
            drop[1] += random.randint(2, 4) if heavy else random.randint(2, 3)
            drop[0] += random.choice([-1, 0, 0, 0])
            if drop[1] >= self.height:
                drop[1] = 0
                drop[0] = random.randint(0, self.width - 1)

        return bg, fg

    def reset(self) -> None:
        self.far_drops.clear()
        self.near_drops.clear()
        self._spawn_far(self._far_count)
        self._spawn_near(self._near_count)


class SnowAnimation(WeatherAnimation):
    """Snow crystals at two depths with intensity scaling.

    Far flakes (behind): 2px horizontal dot pair, moderate brightness, slow drift.
    Near flakes (in front): + shaped crystal, bright white, gentle fall.

    Particle count scales with precipitation_mm:
    - Light (< 1mm): sparse flurry (6 far, 3 near)
    - Moderate (1-3mm): normal snow (10 far, 6 near)
    - Heavy (> 3mm): dense snowfall (16 far, 10 near)
    """

    def __init__(self, width: int = 64, height: int = 24, precipitation_mm: float = 2.0) -> None:
        super().__init__(width, height)
        self.precipitation_mm = precipitation_mm
        self._far_count, self._near_count = self._particle_counts(precipitation_mm)
        self.far_flakes: list[list[int]] = []
        self.near_flakes: list[list[int]] = []
        self._spawn_far(self._far_count)
        self._spawn_near(self._near_count)

    @staticmethod
    def _particle_counts(precipitation_mm: float) -> tuple[int, int]:
        """Return (far_count, near_count) based on precipitation intensity."""
        if precipitation_mm < 1.0:
            return 6, 3
        elif precipitation_mm <= 3.0:
            return 10, 6
        else:
            return 16, 10

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_flakes.append([
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ])

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_flakes.append([
                random.randint(1, self.width - 2),
                random.randint(0, self.height - 1),
            ])

    def _draw_crystal(self, draw: ImageDraw.Draw, x: int, y: int, alpha: int) -> None:
        """Draw a 3x3 snow crystal (+ shape)."""
        color = (255, 255, 255, alpha)
        if 0 <= x < self.width and 0 <= y < self.height:
            draw.point((x, y), fill=color)
        if 0 <= x - 1 < self.width and 0 <= y < self.height:
            draw.point((x - 1, y), fill=color)
        if 0 <= x + 1 < self.width and 0 <= y < self.height:
            draw.point((x + 1, y), fill=color)
        if 0 <= x < self.width and 0 <= y - 1 < self.height:
            draw.point((x, y - 1), fill=color)
        if 0 <= x < self.width and 0 <= y + 1 < self.height:
            draw.point((x, y + 1), fill=color)

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Far flakes -- behind text, 2px horizontal pair, moderate
        for flake in self.far_flakes:
            x, y = flake[0], flake[1]
            if 0 <= x < self.width and 0 <= y < self.height:
                bg_draw.point((x, y), fill=(220, 230, 255, 130))
                if x + 1 < self.width:
                    bg_draw.point((x + 1, y), fill=(220, 230, 255, 100))
            flake[1] += random.choice([0, 0, 1])
            flake[0] += random.choice([-1, 0, 0, 1])
            flake[0] = max(0, min(flake[0], self.width - 1))
            if flake[1] >= self.height:
                flake[1] = 0
                flake[0] = random.randint(0, self.width - 1)

        # Near flakes -- in front of text, + crystal, bright
        for flake in self.near_flakes:
            x, y = flake[0], flake[1]
            self._draw_crystal(fg_draw, x, y, 210)
            flake[1] += random.randint(0, 1)
            flake[0] += random.choice([-1, 0, 0, 1])
            flake[0] = max(1, min(flake[0], self.width - 2))
            if flake[1] >= self.height:
                flake[1] = 0
                flake[0] = random.randint(1, self.width - 2)

        return bg, fg

    def reset(self) -> None:
        self.far_flakes.clear()
        self.near_flakes.clear()
        self._spawn_far(self._far_count)
        self._spawn_near(self._near_count)


class CloudAnimation(WeatherAnimation):
    """Drifting grey-white cloud blobs at two depths."""

    def __init__(self, width: int = 64, height: int = 24) -> None:
        super().__init__(width, height)
        self.far_clouds: list[dict] = [
            {"x": 5.0, "y": 4, "w": 12, "h": 6, "speed": 0.08},
            {"x": 40.0, "y": 14, "w": 10, "h": 5, "speed": 0.06},
        ]
        self.near_clouds: list[dict] = [
            {"x": 25.0, "y": 8, "w": 14, "h": 6, "speed": 0.2},
        ]

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Far clouds -- behind text, moderate
        for cloud in self.far_clouds:
            x, y, w, h = int(cloud["x"]), cloud["y"], cloud["w"], cloud["h"]
            bg_draw.ellipse([x, y, x + w, y + h], fill=(150, 160, 180, 90))
            bg_draw.ellipse([x + w // 3, y - 1, x + w + w // 3, y + h - 1], fill=(150, 160, 180, 70))
            cloud["x"] += cloud["speed"]
            if cloud["x"] > self.width:
                cloud["x"] = float(-cloud["w"])

        # Near clouds -- in front of text, brighter
        for cloud in self.near_clouds:
            x, y, w, h = int(cloud["x"]), cloud["y"], cloud["w"], cloud["h"]
            fg_draw.ellipse([x, y, x + w, y + h], fill=(190, 200, 220, 130))
            fg_draw.ellipse([x + w // 3, y - 1, x + w + w // 3, y + h - 1], fill=(190, 200, 220, 100))
            cloud["x"] += cloud["speed"]
            if cloud["x"] > self.width:
                cloud["x"] = float(-cloud["w"])

        return bg, fg

    def reset(self) -> None:
        self.far_clouds[0]["x"] = 5.0
        self.far_clouds[1]["x"] = 40.0
        self.near_clouds[0]["x"] = 25.0


class SunAnimation(WeatherAnimation):
    """Sun body with rays beaming downward at two depths.

    A small sun circle is drawn in the top-right of the weather zone,
    giving visual context so the rays are recognizable as sunshine.

    Far rays (behind): dimmer, thinner, slower.
    Near rays (in front): brighter, longer, faster -- beaming over text.
    """

    # Sun body position (top-right of weather zone, clear of left-side text)
    _SUN_X = 48
    _SUN_Y = 4
    _SUN_RADIUS = 3

    def __init__(self, width: int = 64, height: int = 24) -> None:
        super().__init__(width, height)
        self.far_rays: list[list[float]] = []
        self.near_rays: list[list[float]] = []
        self._spawn_far(9)
        self._spawn_near(5)

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_rays.append([
                float(random.randint(0, self.width - 1)),
                float(random.randint(0, self.height - 1)),
                random.uniform(0.5, 0.9),   # slower
                random.randint(2, 4),        # shorter
                random.randint(100, 140),    # moderate
            ])

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_rays.append([
                float(random.randint(0, self.width - 1)),
                float(random.randint(0, self.height - 1)),
                random.uniform(1.0, 1.8),    # faster
                random.randint(4, 7),         # longer
                random.randint(160, 220),     # bright
            ])

    def _draw_ray(self, draw: ImageDraw.Draw, ray: list[float], color: tuple) -> None:
        x, y, speed, length, alpha = ray[0], ray[1], ray[2], int(ray[3]), int(ray[4])
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + length * 0.5), int(y + length)
        if 0 <= x1 < self.width and 0 <= y1 < self.height:
            draw.line(
                [(x1, y1), (min(x2, self.width - 1), min(y2, self.height - 1))],
                fill=(*color, alpha),
            )
        ray[0] += speed * 0.4
        ray[1] += speed
        if ray[1] >= self.height or ray[0] >= self.width:
            ray[0] = float(random.randint(0, self.width - 1))
            ray[1] = 0.0

    def _draw_sun_body(self, draw: ImageDraw.Draw) -> None:
        """Draw a warm sun circle with a soft glow in the weather zone."""
        sx, sy, r = self._SUN_X, self._SUN_Y, self._SUN_RADIUS
        # Outer glow (larger, dimmer)
        draw.ellipse(
            [sx - r - 1, sy - r - 1, sx + r + 1, sy + r + 1],
            fill=(255, 200, 40, 80),
        )
        # Sun body (bright warm yellow)
        draw.ellipse(
            [sx - r, sy - r, sx + r, sy + r],
            fill=(255, 220, 60, 200),
        )

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Sun body behind text for context
        self._draw_sun_body(bg_draw)

        for ray in self.far_rays:
            self._draw_ray(bg_draw, ray, (240, 200, 40))

        for ray in self.near_rays:
            self._draw_ray(fg_draw, ray, (255, 240, 60))

        return bg, fg

    def reset(self) -> None:
        self.far_rays.clear()
        self.near_rays.clear()
        self._spawn_far(9)
        self._spawn_near(5)


class ThunderAnimation(WeatherAnimation):
    """Rain with lightning bolts and bright flashes.

    Lightning strikes every ~4 seconds, lasts 3 frames:
    - Frame 1: bright white flash + jagged bolt
    - Frame 2: bolt afterglow
    - Frame 3: dim fade
    """

    def __init__(self, width: int = 64, height: int = 24, precipitation_mm: float = 5.0) -> None:
        super().__init__(width, height)
        self._rain = RainAnimation(width, height, precipitation_mm=precipitation_mm)
        self._tick_count = 0
        self._flash_remaining = 0
        self._bolt_x = 0

    def _draw_bolt(self, draw: ImageDraw.Draw, start_x: int, alpha: int) -> None:
        """Draw a jagged lightning bolt from top to bottom."""
        color = (255, 255, 200, alpha)
        x = start_x
        y = 0
        while y < self.height - 2:
            # Jagged segments: go down 2-4px with random horizontal jag
            seg_len = random.randint(2, 4)
            next_y = min(y + seg_len, self.height - 1)
            jag = random.choice([-3, -2, -1, 1, 2, 3])
            next_x = max(0, min(x + jag, self.width - 1))
            draw.line([(x, y), (next_x, next_y)], fill=color, width=1)
            x, y = next_x, next_y

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg, fg = self._rain.tick()
        self._tick_count += 1

        # Trigger new lightning every ~12 ticks (~4 seconds at 3 FPS)
        if self._tick_count % 12 == 0:
            self._flash_remaining = 3
            self._bolt_x = random.randint(10, self.width - 10)

        if self._flash_remaining > 0:
            fg_draw = ImageDraw.Draw(fg)
            bg_draw = ImageDraw.Draw(bg)

            if self._flash_remaining == 3:
                # Bright flash + bolt
                bg_draw.rectangle(
                    [0, 0, self.width - 1, self.height - 1],
                    fill=(255, 255, 180, 120),
                )
                self._draw_bolt(fg_draw, self._bolt_x, 220)
            elif self._flash_remaining == 2:
                # Bolt afterglow
                self._draw_bolt(fg_draw, self._bolt_x, 150)
            else:
                # Dim fade
                bg_draw.rectangle(
                    [0, 0, self.width - 1, self.height - 1],
                    fill=(200, 200, 150, 40),
                )

            self._flash_remaining -= 1

        return bg, fg

    def reset(self) -> None:
        self._rain.reset()
        self._tick_count = 0
        self._flash_remaining = 0


class FogAnimation(WeatherAnimation):
    """Fog clouds at two depths drifting through the right side of the zone.

    Far clouds (behind): dimmer, smaller, slower.
    Near clouds (in front): brighter, larger, drift over text for 3D misty effect.
    """

    def __init__(self, width: int = 64, height: int = 24) -> None:
        super().__init__(width, height)
        self.far_blobs: list[dict] = []
        self.near_blobs: list[dict] = []
        self._spawn_far(3)
        self._spawn_near(3)

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_blobs.append({
                "x": float(random.randint(21, self.width + 20)),
                "y": random.randint(4, 10),
                "w": random.randint(6, 10),
                "h": random.randint(3, 4),
                "speed": random.uniform(0.05, 0.12),
                "alpha": random.randint(65, 90),
            })

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_blobs.append({
                "x": float(random.randint(21, self.width + 20)),
                "y": random.randint(3, 11),
                "w": random.randint(10, 16),
                "h": random.randint(4, 6),
                "speed": random.uniform(0.12, 0.25),
                "alpha": random.randint(100, 140),
            })

    def _draw_blob(self, draw: ImageDraw.Draw, blob: dict, bright: bool) -> None:
        x = int(blob["x"])
        y, w, h, alpha = blob["y"], blob["w"], blob["h"], blob["alpha"]
        base = (210, 220, 235) if bright else (180, 190, 200)
        draw.ellipse([x, y, x + w, y + h], fill=(*base, alpha))
        draw.ellipse([x + w // 4, y - 1, x + w - w // 4, y + h - 2], fill=(*base, max(alpha - 25, 30)))

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        for blob in self.far_blobs:
            self._draw_blob(bg_draw, blob, bright=False)
            blob["x"] -= blob["speed"]
            if blob["x"] + blob["w"] < 21:
                blob["x"] = float(self.width + random.randint(0, 10))
                blob["y"] = random.randint(4, 10)

        for blob in self.near_blobs:
            self._draw_blob(fg_draw, blob, bright=True)
            blob["x"] -= blob["speed"]
            if blob["x"] + blob["w"] < 21:
                blob["x"] = float(self.width + random.randint(0, 10))
                blob["y"] = random.randint(3, 11)

        return bg, fg

    def reset(self) -> None:
        self.far_blobs.clear()
        self.near_blobs.clear()
        self._spawn_far(3)
        self._spawn_near(3)


class ClearNightAnimation(WeatherAnimation):
    """Twinkling stars for clear nighttime skies at two depths.

    Each star has its own independent twinkle cycle using a state machine:
    - DARK: star is invisible, waiting a random duration before next blink
    - BRIGHTEN: star fades in over a random number of ticks
    - PEAK: star holds at max brightness for a random duration
    - DIM: star fades out over a random number of ticks

    Each star's durations for each phase are independently randomized,
    producing an organic, non-uniform twinkling pattern like a real night sky.

    Far stars (behind text): cool white, dimmer peaks, longer dark intervals.
    Near stars (in front of text): warm white, brighter peaks, + shape at peak.
    """

    # Star state constants
    _DARK = 0
    _BRIGHTEN = 1
    _PEAK = 2
    _DIM = 3

    def __init__(self, width: int = 64, height: int = 24) -> None:
        super().__init__(width, height)
        self.far_stars: list[dict] = []
        self.near_stars: list[dict] = []
        self._spawn_far(14)
        self._spawn_near(6)

    def _new_star(self, *, is_near: bool) -> dict:
        """Create a single star with random position and twinkle parameters."""
        if is_near:
            peak_alpha = random.randint(160, 240)
            dark_ticks = random.randint(4, 20)
            brighten_ticks = random.randint(2, 6)
            peak_ticks = random.randint(3, 10)
            dim_ticks = random.randint(2, 8)
        else:
            peak_alpha = random.randint(80, 150)
            dark_ticks = random.randint(6, 30)
            brighten_ticks = random.randint(3, 10)
            peak_ticks = random.randint(2, 8)
            dim_ticks = random.randint(3, 12)

        # Start each star at a random point in its cycle to avoid sync
        state = random.choice([self._DARK, self._BRIGHTEN, self._PEAK, self._DIM])
        if state == self._DARK:
            timer = random.randint(0, dark_ticks)
        elif state == self._BRIGHTEN:
            timer = random.randint(0, brighten_ticks)
        elif state == self._PEAK:
            timer = random.randint(0, peak_ticks)
        else:
            timer = random.randint(0, dim_ticks)

        return {
            "x": random.randint(0, self.width - 1),
            "y": random.randint(0, self.height - 1),
            "peak_alpha": peak_alpha,
            "state": state,
            "timer": timer,
            "dark_ticks": dark_ticks,
            "brighten_ticks": brighten_ticks,
            "peak_ticks": peak_ticks,
            "dim_ticks": dim_ticks,
        }

    def _randomize_durations(self, star: dict, *, is_near: bool) -> None:
        """Re-randomize phase durations for the next cycle."""
        if is_near:
            star["dark_ticks"] = random.randint(4, 20)
            star["brighten_ticks"] = random.randint(2, 6)
            star["peak_ticks"] = random.randint(3, 10)
            star["dim_ticks"] = random.randint(2, 8)
            star["peak_alpha"] = random.randint(160, 240)
        else:
            star["dark_ticks"] = random.randint(6, 30)
            star["brighten_ticks"] = random.randint(3, 10)
            star["peak_ticks"] = random.randint(2, 8)
            star["dim_ticks"] = random.randint(3, 12)
            star["peak_alpha"] = random.randint(80, 150)

    def _spawn_far(self, count: int) -> None:
        for _ in range(count):
            self.far_stars.append(self._new_star(is_near=False))

    def _spawn_near(self, count: int) -> None:
        for _ in range(count):
            self.near_stars.append(self._new_star(is_near=True))

    def _tick_star(self, star: dict, *, is_near: bool) -> int:
        """Advance star state machine by one tick, return current alpha (0-255)."""
        state = star["state"]
        timer = star["timer"]

        if state == self._DARK:
            alpha = 0
            star["timer"] -= 1
            if star["timer"] <= 0:
                star["state"] = self._BRIGHTEN
                star["timer"] = star["brighten_ticks"]
        elif state == self._BRIGHTEN:
            # Linear fade in: progress from 0.0 to 1.0
            total = star["brighten_ticks"]
            elapsed = total - timer
            progress = elapsed / max(total, 1)
            alpha = int(star["peak_alpha"] * progress)
            star["timer"] -= 1
            if star["timer"] <= 0:
                star["state"] = self._PEAK
                star["timer"] = star["peak_ticks"]
        elif state == self._PEAK:
            alpha = star["peak_alpha"]
            star["timer"] -= 1
            if star["timer"] <= 0:
                star["state"] = self._DIM
                star["timer"] = star["dim_ticks"]
        else:  # DIM
            # Linear fade out: progress from 1.0 to 0.0
            total = star["dim_ticks"]
            progress = timer / max(total, 1)
            alpha = int(star["peak_alpha"] * progress)
            star["timer"] -= 1
            if star["timer"] <= 0:
                star["state"] = self._DARK
                self._randomize_durations(star, is_near=is_near)
                star["timer"] = star["dark_ticks"]

        return max(0, min(alpha, 255))

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        bg_draw = ImageDraw.Draw(bg)
        fg_draw = ImageDraw.Draw(fg)

        # Far stars -- behind text, cool white, single pixel
        for star in self.far_stars:
            alpha = self._tick_star(star, is_near=False)
            if alpha > 0:
                x, y = star["x"], star["y"]
                if 0 <= x < self.width and 0 <= y < self.height:
                    bg_draw.point((x, y), fill=(180, 200, 255, alpha))

        # Near stars -- in front of text, warm white, + shape at peak
        for star in self.near_stars:
            alpha = self._tick_star(star, is_near=True)
            if alpha > 0:
                x, y = star["x"], star["y"]
                color = (255, 250, 230, alpha)
                if 0 <= x < self.width and 0 <= y < self.height:
                    fg_draw.point((x, y), fill=color)
                    # Cross arms when bright enough
                    if alpha > 150:
                        dim_color = (255, 250, 230, alpha // 2)
                        if 0 <= x - 1 < self.width:
                            fg_draw.point((x - 1, y), fill=dim_color)
                        if 0 <= x + 1 < self.width:
                            fg_draw.point((x + 1, y), fill=dim_color)
                        if 0 <= y - 1 < self.height:
                            fg_draw.point((x, y - 1), fill=dim_color)
                        if 0 <= y + 1 < self.height:
                            fg_draw.point((x, y + 1), fill=dim_color)

        return bg, fg

    def reset(self) -> None:
        self.far_stars.clear()
        self.near_stars.clear()
        self._spawn_far(14)
        self._spawn_near(6)


class CompositeAnimation(WeatherAnimation):
    """Layers multiple weather animations by alpha-compositing their frames.

    Each child animation's bg layers are composited together, and fg layers
    are composited together, preserving the depth-layer rendering pipeline.
    """

    def __init__(self, animations: list[WeatherAnimation]) -> None:
        width = animations[0].width if animations else 64
        height = animations[0].height if animations else 24
        super().__init__(width, height)
        self.animations = animations

    def tick(self) -> tuple[Image.Image, Image.Image]:
        bg = self._empty()
        fg = self._empty()
        for anim in self.animations:
            child_bg, child_fg = anim.tick()
            bg = Image.alpha_composite(bg, child_bg)
            fg = Image.alpha_composite(fg, child_fg)
        return bg, fg

    def reset(self) -> None:
        for anim in self.animations:
            anim.reset()


# Factory: weather group name -> animation class (daytime)
_ANIMATION_MAP: dict[str, type[WeatherAnimation]] = {
    "clear": SunAnimation,
    "partcloud": SunAnimation,
    "cloudy": CloudAnimation,
    "rain": RainAnimation,
    "sleet": RainAnimation,
    "snow": SnowAnimation,
    "thunder": ThunderAnimation,
    "fog": FogAnimation,
}

# Night overrides: groups that should use a different animation at night
_NIGHT_ANIMATION_MAP: dict[str, type[WeatherAnimation]] = {
    "clear": ClearNightAnimation,
    "partcloud": ClearNightAnimation,
}


def get_animation(
    weather_group: str,
    *,
    is_night: bool = False,
    precipitation_mm: float = 0.0,
) -> WeatherAnimation:
    """Get an animation instance for the given weather group and time of day.

    At night, "clear" and "partcloud" use twinkling stars instead of sunrays.
    Other weather groups (rain, snow, etc.) are the same day and night.

    Rain and thunder animations scale particle density based on precipitation_mm.

    Args:
        weather_group: One of the icon group names from weather_icons.py
                       (clear, partcloud, cloudy, rain, sleet, snow, thunder, fog).
        is_night: True if it's nighttime (from MET symbol_code suffix).
        precipitation_mm: Precipitation amount in mm/h for rain intensity scaling.

    Returns:
        A WeatherAnimation instance that produces overlay frames.
    """
    if is_night:
        cls = _NIGHT_ANIMATION_MAP.get(weather_group)
        if cls is not None:
            return cls()
    cls = _ANIMATION_MAP.get(weather_group, CloudAnimation)
    if cls is RainAnimation:
        return RainAnimation(precipitation_mm=precipitation_mm)
    if cls is ThunderAnimation:
        return ThunderAnimation(precipitation_mm=precipitation_mm)
    return cls()
