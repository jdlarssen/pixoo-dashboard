"""Tests for weather animation visibility on LED hardware.

Enforces minimum alpha and pixel-coverage thresholds that guarantee
animation visibility on the Pixoo 64 LED matrix. Serves as a regression
gate so animation cannot be accidentally dimmed below visibility again.
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
        return max(alpha_band.getdata())

    def _count_non_transparent_pixels(self, frame: Image.Image) -> int:
        """Count pixels with alpha > 0."""
        alpha_band = frame.split()[3]
        return sum(1 for a in alpha_band.getdata() if a > 0)

    def test_rain_alpha_above_minimum(self):
        anim = RainAnimation()
        frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 100, f"Rain max alpha {max_a} too low for LED visibility"

    def test_snow_alpha_above_minimum(self):
        anim = SnowAnimation()
        frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 90, f"Snow max alpha {max_a} too low for LED visibility"

    def test_cloud_alpha_above_minimum(self):
        anim = CloudAnimation()
        frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 60, f"Cloud max alpha {max_a} too low for LED visibility"

    def test_sun_alpha_above_minimum(self):
        anim = SunAnimation()
        frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 40, f"Sun max alpha {max_a} too low for LED visibility"

    def test_thunder_flash_alpha(self):
        anim = ThunderAnimation()
        # Tick to the flash frame (tick 20)
        for _ in range(20):
            frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 120, f"Thunder flash alpha {max_a} too low"

    def test_fog_alpha_above_minimum(self):
        anim = FogAnimation()
        frame = anim.tick()
        max_a = self._max_alpha_in_frame(frame)
        assert max_a >= 60, f"Fog max alpha {max_a} too low for LED visibility"

    def test_rain_has_multi_pixel_particles(self):
        """Rain drops should be larger than single pixels."""
        anim = RainAnimation()
        frame = anim.tick()
        non_transparent = self._count_non_transparent_pixels(frame)
        # 22 drops * at least 2 pixels each = at least 40
        assert non_transparent >= 40, (
            f"Rain only has {non_transparent} non-transparent pixels -- particles too small"
        )

    def test_snow_has_multi_pixel_particles(self):
        """Snow flakes should be larger than single pixels."""
        anim = SnowAnimation()
        frame = anim.tick()
        non_transparent = self._count_non_transparent_pixels(frame)
        # 15 flakes * ~2 pixels each, minus edge clipping and overlaps = at least 20
        assert non_transparent >= 20, (
            f"Snow only has {non_transparent} non-transparent pixels -- particles too small"
        )

    def test_all_frames_are_rgba_64x20(self):
        """All animation frames must be 64x20 RGBA."""
        for name in ["clear", "rain", "snow", "cloudy", "thunder", "fog"]:
            anim = get_animation(name)
            frame = anim.tick()
            assert frame.size == (64, 20), f"{name} frame size {frame.size} != (64, 20)"
            assert frame.mode == "RGBA", f"{name} frame mode {frame.mode} != RGBA"

    def test_get_animation_returns_correct_types(self):
        assert isinstance(get_animation("rain"), RainAnimation)
        assert isinstance(get_animation("snow"), SnowAnimation)
        assert isinstance(get_animation("cloudy"), CloudAnimation)
        assert isinstance(get_animation("fog"), FogAnimation)
