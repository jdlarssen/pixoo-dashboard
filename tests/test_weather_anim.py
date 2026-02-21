"""Tests for weather animation visibility on LED hardware.

Enforces minimum alpha and pixel-coverage thresholds that guarantee
animation visibility on the Pixoo 64 LED matrix. Serves as a regression
gate so animation cannot be accidentally dimmed below visibility again.

Animations return (bg_layer, fg_layer) tuples for 3D depth effect.
"""

from PIL import Image

from src.display.weather_anim import (
    CloudAnimation,
    FogAnimation,
    RainAnimation,
    SnowAnimation,
    SunAnimation,
    ThunderAnimation,
    get_animation,
)


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
