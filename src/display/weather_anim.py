"""Animated weather backgrounds for the 64x20 weather zone.

Provides ambient animation overlays (RGBA) that render behind weather text.
Each animation class produces low-alpha particle effects so text remains readable.
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
    """Falling blue raindrop particles."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self.drops: list[list[int]] = []
        self._spawn_drops(18)

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
            # Draw raindrop as a 1px blue dot
            if 0 <= drop[0] < self.width and 0 <= drop[1] < self.height:
                draw.point((drop[0], drop[1]), fill=(80, 160, 255, 50))
            # Move down with slight horizontal drift
            drop[1] += random.randint(2, 3)
            drop[0] += random.choice([-1, 0, 0, 0])
            # Wrap to top when off-screen
            if drop[1] >= self.height:
                drop[1] = 0
                drop[0] = random.randint(0, self.width - 1)
        return img

    def reset(self) -> None:
        self.drops.clear()
        self._spawn_drops(18)


class SnowAnimation(WeatherAnimation):
    """Gently falling white snowflake particles."""

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
            if 0 <= flake[0] < self.width and 0 <= flake[1] < self.height:
                draw.point((flake[0], flake[1]), fill=(255, 255, 255, 45))
            # Slow descent with horizontal drift
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
        # 3 cloud blobs at different positions and speeds
        self.clouds: list[dict] = [
            {"x": 5.0, "y": 3, "w": 12, "h": 6, "speed": 0.3},
            {"x": 30.0, "y": 8, "w": 10, "h": 5, "speed": 0.2},
            {"x": 50.0, "y": 13, "w": 14, "h": 5, "speed": 0.4},
        ]

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for cloud in self.clouds:
            x = int(cloud["x"])
            y = cloud["y"]
            w = cloud["w"]
            h = cloud["h"]
            # Draw cloud as overlapping ellipses at low alpha
            draw.ellipse(
                [x, y, x + w, y + h],
                fill=(180, 180, 190, 35),
            )
            draw.ellipse(
                [x + w // 3, y - 1, x + w + w // 3, y + h - 1],
                fill=(180, 180, 190, 30),
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
    """Subtle warm glow pulsing effect for sunny conditions."""

    def __init__(self, width: int = 64, height: int = 20) -> None:
        super().__init__(width, height)
        self._tick_count = 0

    def tick(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Gentle pulsing glow: alpha oscillates between 15 and 35
        self._tick_count += 1
        phase = (self._tick_count % 20) / 20.0
        alpha = int(15 + 20 * abs(phase - 0.5) * 2)
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
        # Flash every ~20 ticks (roughly every 5 seconds at 4 FPS)
        if self._tick_count % 20 == 0:
            draw = ImageDraw.Draw(img)
            # Brief bright flash across zone
            draw.rectangle(
                [0, 0, self.width - 1, self.height - 1],
                fill=(255, 255, 255, 40),
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
        self._offset += 0.15
        # Draw horizontal fog bands at varying positions
        for i, base_y in enumerate([3, 8, 13, 17]):
            y = int(base_y + (self._offset + i * 1.5) % 3 - 1)
            if 0 <= y < self.height:
                alpha = 30 + (i % 2) * 15
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
