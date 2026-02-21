"""Tests for weather animation visibility and color identity on LED hardware.

Enforces minimum alpha and pixel-coverage thresholds that guarantee
animation visibility on the Pixoo 64 LED matrix. Serves as a regression
gate so animation cannot be accidentally dimmed below visibility again.

Also validates color-identity properties (channel dominance, contrast ratios)
to prevent weather text/particle color clashes from recurring.

Animations return (bg_layer, fg_layer) tuples for 3D depth effect.
"""

import math

from PIL import Image

from src.display.layout import COLOR_WEATHER_RAIN
from src.display.weather_anim import (
    CloudAnimation,
    FogAnimation,
    RainAnimation,
    SnowAnimation,
    SunAnimation,
    ThunderAnimation,
    get_animation,
)


def _sample_particle_rgb(anim, num_ticks=5):
    """Collect all non-transparent pixel RGB values from multiple animation ticks.

    For each tick, iterates both bg and fg layers and collects (r, g, b)
    for pixels where alpha > 0.

    Returns:
        List of (r, g, b) tuples.
    """
    colors = []
    for _ in range(num_ticks):
        bg, fg = anim.tick()
        for layer in (bg, fg):
            # get_flattened_data() on RGBA returns tuples of (R, G, B, A)
            for pixel in layer.get_flattened_data():
                r, g, b, a = pixel
                if a > 0:
                    colors.append((r, g, b))
    return colors


def relative_luminance(r, g, b):
    """WCAG 2.0 relative luminance from sRGB values (0-255)."""
    channels = []
    for c in (r, g, b):
        c_norm = c / 255.0
        if c_norm <= 0.03928:
            channels.append(c_norm / 12.92)
        else:
            channels.append(((c_norm + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(color1, color2):
    """WCAG contrast ratio between two (r, g, b) tuples."""
    l1 = relative_luminance(*color1)
    l2 = relative_luminance(*color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestAnimationVisibility:
    """Verify animation frames produce LED-visible pixel values."""

    def _max_alpha_in_frame(self, frame: Image.Image) -> int:
        """Return the maximum alpha value found in an RGBA frame."""
        alpha_band = frame.split()[3]
        return max(alpha_band.get_flattened_data())

    def _max_alpha_in_layers(self, layers: tuple[Image.Image, Image.Image]) -> int:
        """Return the maximum alpha across both bg and fg layers."""
        return max(self._max_alpha_in_frame(layers[0]), self._max_alpha_in_frame(layers[1]))

    def _count_non_transparent_pixels(self, frame: Image.Image) -> int:
        """Count pixels with alpha > 0."""
        alpha_band = frame.split()[3]
        return sum(1 for a in alpha_band.get_flattened_data() if a > 0)

    def _count_non_transparent_in_layers(self, layers: tuple[Image.Image, Image.Image]) -> int:
        """Count non-transparent pixels across both layers."""
        return self._count_non_transparent_pixels(layers[0]) + self._count_non_transparent_pixels(layers[1])

    def test_rain_alpha_above_minimum(self):
        anim = RainAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 100, f"Rain max alpha {max_a} too low for LED visibility"

    def test_snow_alpha_above_minimum(self):
        anim = SnowAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 90, f"Snow max alpha {max_a} too low for LED visibility"

    def test_cloud_alpha_above_minimum(self):
        anim = CloudAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 60, f"Cloud max alpha {max_a} too low for LED visibility"

    def test_sun_alpha_above_minimum(self):
        anim = SunAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 40, f"Sun max alpha {max_a} too low for LED visibility"

    def test_thunder_flash_alpha(self):
        anim = ThunderAnimation()
        # Tick to the flash frame (tick 20)
        for _ in range(20):
            layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 120, f"Thunder flash alpha {max_a} too low"

    def test_fog_alpha_above_minimum(self):
        anim = FogAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 60, f"Fog max alpha {max_a} too low for LED visibility"

    def test_rain_has_multi_pixel_particles(self):
        """Rain drops should be larger than single pixels."""
        anim = RainAnimation()
        layers = anim.tick()
        non_transparent = self._count_non_transparent_in_layers(layers)
        # Far + near drops across both layers
        assert non_transparent >= 30, (
            f"Rain only has {non_transparent} non-transparent pixels -- particles too small"
        )

    def test_snow_has_multi_pixel_particles(self):
        """Snow flakes should be larger than single pixels."""
        anim = SnowAnimation()
        layers = anim.tick()
        non_transparent = self._count_non_transparent_in_layers(layers)
        assert non_transparent >= 20, (
            f"Snow only has {non_transparent} non-transparent pixels -- particles too small"
        )

    def test_tick_returns_two_layers(self):
        """All animations must return (bg_layer, fg_layer) tuple."""
        for name in ["clear", "rain", "snow", "cloudy", "thunder", "fog"]:
            anim = get_animation(name)
            result = anim.tick()
            assert isinstance(result, tuple), f"{name} tick() should return tuple"
            assert len(result) == 2, f"{name} tick() should return 2 layers"
            bg, fg = result
            assert bg.size == (64, 24), f"{name} bg size {bg.size} != (64, 24)"
            assert bg.mode == "RGBA", f"{name} bg mode {bg.mode} != RGBA"
            assert fg.size == (64, 24), f"{name} fg size {fg.size} != (64, 24)"
            assert fg.mode == "RGBA", f"{name} fg mode {fg.mode} != RGBA"

    def test_get_animation_returns_correct_types(self):
        assert isinstance(get_animation("rain"), RainAnimation)
        assert isinstance(get_animation("snow"), SnowAnimation)
        assert isinstance(get_animation("cloudy"), CloudAnimation)
        assert isinstance(get_animation("fog"), FogAnimation)


class TestColorIdentity:
    """Validate weather animation color properties using channel-dominance assertions.

    These tests catch hue-family collisions (e.g., blue rain text on blue rain
    particles) without asserting exact RGB values, so they survive minor palette
    tweaks while preventing color identity regressions.
    """

    def _avg_rgb(self, colors):
        """Return average (r, g, b) from a list of RGB tuples."""
        if not colors:
            return (0, 0, 0)
        n = len(colors)
        avg_r = sum(c[0] for c in colors) / n
        avg_g = sum(c[1] for c in colors) / n
        avg_b = sum(c[2] for c in colors) / n
        return (avg_r, avg_g, avg_b)

    def test_rain_particles_are_blue_dominant(self):
        """Rain particles should have B channel dominant over R and G."""
        anim = RainAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No rain particles sampled"
        avg_r, avg_g, avg_b = self._avg_rgb(colors)
        assert avg_b > avg_r + 20, (
            f"Rain B channel ({avg_b:.0f}) not dominant over R ({avg_r:.0f}) by margin 20"
        )
        assert avg_b > avg_g + 20, (
            f"Rain B channel ({avg_b:.0f}) not dominant over G ({avg_g:.0f}) by margin 20"
        )

    def test_snow_particles_are_white_ish(self):
        """Snow particles should be bright with all channels high and low spread."""
        anim = SnowAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No snow particles sampled"
        avg_r, avg_g, avg_b = self._avg_rgb(colors)
        min_channel = min(avg_r, avg_g, avg_b)
        spread = max(avg_r, avg_g, avg_b) - min_channel
        assert min_channel >= 180, (
            f"Snow min channel ({min_channel:.0f}) too low -- should be bright white"
        )
        assert spread <= 50, (
            f"Snow channel spread ({spread:.0f}) too high -- should be near-white"
        )

    def test_sun_particles_are_yellow_dominant(self):
        """Sun particles should have high R and G, low B (yellow)."""
        anim = SunAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No sun particles sampled"
        avg_r, avg_g, avg_b = self._avg_rgb(colors)
        assert avg_r > avg_b + 50, (
            f"Sun R ({avg_r:.0f}) not dominant over B ({avg_b:.0f}) by margin 50"
        )
        assert avg_g > avg_b + 30, (
            f"Sun G ({avg_g:.0f}) not dominant over B ({avg_b:.0f}) by margin 30"
        )

    def test_cloud_particles_are_grey(self):
        """Cloud particles should be neutral grey with low channel spread."""
        anim = CloudAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No cloud particles sampled"
        avg_r, avg_g, avg_b = self._avg_rgb(colors)
        spread = max(avg_r, avg_g, avg_b) - min(avg_r, avg_g, avg_b)
        assert spread <= 40, (
            f"Cloud channel spread ({spread:.0f}) too high -- should be neutral grey"
        )

    def test_fog_particles_are_grey(self):
        """Fog particles should be neutral grey with low channel spread."""
        anim = FogAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No fog particles sampled"
        avg_r, avg_g, avg_b = self._avg_rgb(colors)
        spread = max(avg_r, avg_g, avg_b) - min(avg_r, avg_g, avg_b)
        assert spread <= 40, (
            f"Fog channel spread ({spread:.0f}) too high -- should be neutral grey"
        )

    def test_rain_text_contrasts_with_rain_particles(self):
        """Rain text color must have sufficient luminance contrast against rain particles."""
        anim = RainAnimation()
        colors = _sample_particle_rgb(anim)
        assert len(colors) > 0, "No rain particles sampled"
        avg_particle = self._avg_rgb(colors)
        avg_particle_int = tuple(int(c) for c in avg_particle)
        ratio = contrast_ratio(COLOR_WEATHER_RAIN, avg_particle_int)
        assert ratio >= 2.5, (
            f"Rain text contrast ratio ({ratio:.2f}) too low against particles -- "
            f"text {COLOR_WEATHER_RAIN}, avg particle {avg_particle_int}"
        )

    def test_rain_and_snow_particles_are_distinguishable(self):
        """Rain and snow particles must be visually distinct in RGB space."""
        rain_anim = RainAnimation()
        snow_anim = SnowAnimation()
        rain_colors = _sample_particle_rgb(rain_anim)
        snow_colors = _sample_particle_rgb(snow_anim)
        assert len(rain_colors) > 0, "No rain particles sampled"
        assert len(snow_colors) > 0, "No snow particles sampled"
        rain_avg = self._avg_rgb(rain_colors)
        snow_avg = self._avg_rgb(snow_colors)
        distance = math.sqrt(
            (rain_avg[0] - snow_avg[0]) ** 2
            + (rain_avg[1] - snow_avg[1]) ** 2
            + (rain_avg[2] - snow_avg[2]) ** 2
        )
        assert distance >= 50, (
            f"Rain/snow RGB distance ({distance:.0f}) too small -- "
            f"rain avg {tuple(int(c) for c in rain_avg)}, "
            f"snow avg {tuple(int(c) for c in snow_avg)}"
        )

    def test_thunder_inherits_rain_blue_dominance(self):
        """Thunder animation should have significant blue-dominant pixels from rain component."""
        anim = ThunderAnimation()
        colors = _sample_particle_rgb(anim, num_ticks=10)
        assert len(colors) > 0, "No thunder particles sampled"
        blue_dominant_count = sum(
            1 for r, g, b in colors if b > r + 10 and b > g + 10
        )
        proportion = blue_dominant_count / len(colors)
        assert proportion >= 0.30, (
            f"Thunder blue-dominant proportion ({proportion:.2f}) too low -- "
            f"rain component should produce at least 30% blue pixels"
        )
