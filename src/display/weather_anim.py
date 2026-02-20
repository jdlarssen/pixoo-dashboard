"""Animated weather backgrounds for the 64x20 weather zone.

Provides ambient animation overlays (RGBA) that render behind weather text.
Alpha values are tuned for LED hardware visibility (65-150 range) -- lower
values produce no visible light on the Pixoo 64's LED matrix.
"""

import random

from PIL import Image, ImageDraw


class WeatherAnimation:
    """Base class for weather zone background animations.

    Produces 64x20 RGBA overlay images. Subclasses override tick() to
    generate per-frame particle effects.
    """

    def __init__(self, width: int = 64, height: int = 20) -> None:
        self.width = width
        self.height = height

    def tick(self) -> Image.Image:
        """Return the next animation frame as an RGBA image."""
        return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def reset(self) -> None:
        """Reset animation state to initial conditions."""


class ClearAnimation(WeatherAnimation):
    """Minimal animation for clear skies -- transparent overlay."""

    def tick(self) -> Image.Image:
        return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))


class RainAnimation(WeatherAnimation):
    """Falling blue raindrop particles (2px vertical streaks)."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self.drops: list[list[int]] = []
        self._spawn_drops(22)

    def _spawn_drops(self, count: int) -> None:
        """Create initial raindrop positions spread across the zone."""
        for _ in range(count):
            self.drops.append([
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ])

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for drop in self.drops:
            # Draw raindrop as a 1x2 vertical streak for LED visibility
            x, y = drop[0], drop[1]
            if 0 <= x < self.width and 0 <= y < self.height:
                draw.line([(x, y), (x, min(y + 1, self.height - 1))], fill=(80, 160, 255, 120))
            # Move down with slight horizontal drift (slower for ~3 FPS)
            drop[1] += random.randint(1, 2)
            drop[0] += random.choice([-1, 0, 0, 0])
            # Wrap to top when off-screen
            if drop[1] >= self.height:
                drop[1] = 0
                drop[0] = random.randint(0, self.width - 1)
        return img

    def reset(self) -> None:
        self.drops.clear()
        self._spawn_drops(22)


class SnowAnimation(WeatherAnimation):
    """Gently falling white snowflake particles (2x1 rectangles)."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self.flakes: list[list[int]] = []
        self._spawn_flakes(15)

    def _spawn_flakes(self, count: int) -> None:
        for _ in range(count):
            self.flakes.append([
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ])

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for flake in self.flakes:
            x, y = flake[0], flake[1]
            if 0 <= x < self.width and 0 <= y < self.height:
                # Draw snowflake as a 2x1 horizontal rectangle for LED visibility
                draw.rectangle([x, y, min(x + 1, self.width - 1), y], fill=(255, 255, 255, 110))
            # Slow descent with horizontal drift (already slow enough for ~3 FPS)
            flake[1] += random.randint(1, 2)
            flake[0] += random.choice([-1, 0, 0, 1])
            if flake[1] >= self.height:
                flake[1] = 0
                flake[0] = random.randint(0, self.width - 1)
        return img

    def reset(self) -> None:
        self.flakes.clear()
        self._spawn_flakes(15)


class CloudAnimation(WeatherAnimation):
    """Slowly drifting gray cloud blobs."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        # 3 cloud blobs at different positions and speeds (halved for ~3 FPS)
        self.clouds: list[dict] = [
            {"x": 5.0, "y": 3, "w": 12, "h": 6, "speed": 0.15},
            {"x": 30.0, "y": 8, "w": 10, "h": 5, "speed": 0.1},
            {"x": 50.0, "y": 13, "w": 14, "h": 5, "speed": 0.2},
        ]

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for cloud in self.clouds:
            x = int(cloud["x"])
            y = cloud["y"]
            w = cloud["w"]
            h = cloud["h"]
            # Draw cloud as overlapping ellipses -- alpha tuned for LED visibility
            draw.ellipse(
                [x, y, x + w, y + h],
                fill=(180, 180, 190, 80),
            )
            draw.ellipse(
                [x + w // 3, y - 1, x + w + w // 3, y + h - 1],
                fill=(180, 180, 190, 65),
            )
            # Drift right, wrap around
            cloud["x"] += cloud["speed"]
            if cloud["x"] > self.width:
                cloud["x"] = float(-cloud["w"])
        return img

    def reset(self) -> None:
        self.clouds[0]["x"] = 5.0
        self.clouds[1]["x"] = 30.0
        self.clouds[2]["x"] = 50.0


class SunAnimation(WeatherAnimation):
    """Warm glow pulsing effect for sunny conditions."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self._tick_count = 0

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Pulsing glow: alpha oscillates between 50 and 90 for LED visibility
        self._tick_count += 1
        phase = (self._tick_count % 20) / 20.0
        alpha = int(50 + 40 * abs(phase - 0.5) * 2)
        # Warm gradient from top-left corner
        draw.ellipse(
            [-10, -10, 25, 15],
            fill=(255, 200, 50, alpha),
        )
        return img

    def reset(self) -> None:
        self._tick_count = 0


class ThunderAnimation(WeatherAnimation):
    """Rain with occasional lightning flash."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self._rain = RainAnimation(width, height)
        self._tick_count = 0

    def tick(self) -> Image.Image:
        img = self._rain.tick()
        self._tick_count += 1
        # Flash every ~20 ticks (roughly every 7 seconds at ~3 FPS)
        if self._tick_count % 20 == 0:
            draw = ImageDraw.Draw(img)
            # Bright visible flash across zone
            draw.rectangle(
                [0, 0, self.width - 1, self.height - 1],
                fill=(255, 255, 255, 150),
            )
        return img

    def reset(self) -> None:
        self._rain.reset()
        self._tick_count = 0


class FogAnimation(WeatherAnimation):
    """Slow-moving horizontal gray bands."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self._offset = 0.0

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        self._offset += 0.08  # slower for ~3 FPS (was 0.15 at ~1 effective FPS)
        # Draw horizontal fog bands at varying positions
        for i, base_y in enumerate([3, 8, 13, 17]):
            y = int(base_y + (self._offset + i * 1.5) % 3 - 1)
            if 0 <= y < self.height:
                alpha = 70 + (i % 2) * 30  # LED-visible alpha range
                x_start = int((self._offset * (i + 1)) % 5)
                draw.line(
                    [(x_start, y), (self.width - 1 - x_start, y)],
                    fill=(180, 180, 190, alpha),
                )
        return img

    def reset(self) -> None:
        self._offset = 0.0


# Factory: weather group name -> animation class
_ANIMATION_MAP: dict[str, type[WeatherAnimation]] = {
    "clear": ClearAnimation,
    "partcloud": ClearAnimation,  # subtle -- icon already shows condition
    "cloudy": CloudAnimation,
    "rain": RainAnimation,
    "sleet": RainAnimation,  # similar visual to rain
    "snow": SnowAnimation,
    "thunder": ThunderAnimation,
    "fog": FogAnimation,
}


def get_animation(weather_group: str) -> WeatherAnimation:
    """Get an animation instance for the given weather group.

    Args:
        weather_group: One of the icon group names from weather_icons.py
                       (clear, partcloud, cloudy, rain, sleet, snow, thunder, fog).

    Returns:
        A WeatherAnimation instance that produces overlay frames.
    """
    cls = _ANIMATION_MAP.get(weather_group, CloudAnimation)
    return cls()
