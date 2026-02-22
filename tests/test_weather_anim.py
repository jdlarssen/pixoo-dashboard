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
    ClearNightAnimation,
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
        assert max_a >= 140, f"Rain max alpha {max_a} too low for LED visibility"

    def test_snow_alpha_above_minimum(self):
        anim = SnowAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 130, f"Snow max alpha {max_a} too low for LED visibility"

    def test_cloud_alpha_above_minimum(self):
        anim = CloudAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 90, f"Cloud max alpha {max_a} too low for LED visibility"

    def test_sun_alpha_above_minimum(self):
        anim = SunAnimation()
        layers = anim.tick()
        max_a = self._max_alpha_in_layers(layers)
        assert max_a >= 100, f"Sun max alpha {max_a} too low for LED visibility"

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
        assert max_a >= 90, f"Fog max alpha {max_a} too low for LED visibility"

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
        """All animations (day and night) must return (bg_layer, fg_layer) tuple."""
        for name in ["clear", "rain", "snow", "cloudy", "thunder", "fog"]:
            for is_night in (False, True):
                label = f"{name}/{'night' if is_night else 'day'}"
                anim = get_animation(name, is_night=is_night)
                result = anim.tick()
                assert isinstance(result, tuple), f"{label} tick() should return tuple"
                assert len(result) == 2, f"{label} tick() should return 2 layers"
                bg, fg = result
                assert bg.size == (64, 24), f"{label} bg size {bg.size} != (64, 24)"
                assert bg.mode == "RGBA", f"{label} bg mode {bg.mode} != RGBA"
                assert fg.size == (64, 24), f"{label} fg size {fg.size} != (64, 24)"
                assert fg.mode == "RGBA", f"{label} fg mode {fg.mode} != RGBA"

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


class TestNightAnimations:
    """Verify night-specific animations and day/night animation selection."""

    def test_clear_night_returns_star_animation(self):
        """get_animation('clear', is_night=True) should return ClearNightAnimation."""
        anim = get_animation("clear", is_night=True)
        assert isinstance(anim, ClearNightAnimation), (
            f"Expected ClearNightAnimation, got {type(anim).__name__}"
        )

    def test_partcloud_night_returns_star_animation(self):
        """get_animation('partcloud', is_night=True) should return ClearNightAnimation."""
        anim = get_animation("partcloud", is_night=True)
        assert isinstance(anim, ClearNightAnimation), (
            f"Expected ClearNightAnimation, got {type(anim).__name__}"
        )

    def test_clear_day_returns_sun_animation(self):
        """get_animation('clear') should still return SunAnimation by default."""
        anim = get_animation("clear")
        assert isinstance(anim, SunAnimation), (
            f"Expected SunAnimation, got {type(anim).__name__}"
        )

    def test_clear_day_explicit_returns_sun_animation(self):
        """get_animation('clear', is_night=False) should return SunAnimation."""
        anim = get_animation("clear", is_night=False)
        assert isinstance(anim, SunAnimation), (
            f"Expected SunAnimation, got {type(anim).__name__}"
        )

    def test_rain_night_same_as_day(self):
        """Rain animation should be the same class day and night."""
        day_anim = get_animation("rain", is_night=False)
        night_anim = get_animation("rain", is_night=True)
        assert type(day_anim) is type(night_anim), (
            f"Rain day ({type(day_anim).__name__}) != night ({type(night_anim).__name__})"
        )

    def test_clear_night_tick_returns_two_layers(self):
        """ClearNightAnimation tick should return (bg, fg) RGBA layers."""
        anim = ClearNightAnimation()
        bg, fg = anim.tick()
        assert bg.size == (64, 24), f"bg size {bg.size} != (64, 24)"
        assert bg.mode == "RGBA", f"bg mode {bg.mode} != RGBA"
        assert fg.size == (64, 24), f"fg size {fg.size} != (64, 24)"
        assert fg.mode == "RGBA", f"fg mode {fg.mode} != RGBA"

    def test_clear_night_has_visible_pixels(self):
        """Star animation should produce visible pixels after a few ticks."""
        anim = ClearNightAnimation()
        max_alpha = 0
        total_pixels = 0
        for _ in range(5):
            bg, fg = anim.tick()
            for layer in (bg, fg):
                alpha_band = layer.split()[3]
                for a in alpha_band.get_flattened_data():
                    if a > 0:
                        total_pixels += 1
                    max_alpha = max(max_alpha, a)
        assert max_alpha >= 60, (
            f"Star max alpha {max_alpha} too low for LED visibility"
        )
        assert total_pixels > 0, "No visible star pixels produced"

    def test_clear_night_stars_are_cool_or_warm_white(self):
        """Star particles should be white-ish (cool or warm), not colored."""
        anim = ClearNightAnimation()
        colors = _sample_particle_rgb(anim, num_ticks=5)
        assert len(colors) > 0, "No star particles sampled"
        for r, g, b in colors:
            min_ch = min(r, g, b)
            max_ch = max(r, g, b)
            spread = max_ch - min_ch
            assert spread <= 80, (
                f"Star pixel ({r}, {g}, {b}) spread {spread} too high -- "
                f"should be white-ish"
            )


class TestStarRandomness:
    """Verify ClearNightAnimation produces organic, non-uniform twinkle patterns.

    Stars should NOT all blink in lockstep. Each star should have independent
    timing so the overall effect feels like a real night sky.
    """

    def test_stars_have_varied_peak_alphas(self):
        """Different stars should have different peak brightness levels."""
        anim = ClearNightAnimation()
        peak_alphas = set()
        for star in anim.far_stars + anim.near_stars:
            peak_alphas.add(star["peak_alpha"])
        # With 20 stars, random peak_alpha should produce at least 5 distinct values
        assert len(peak_alphas) >= 5, (
            f"Only {len(peak_alphas)} distinct peak alphas across {len(anim.far_stars) + len(anim.near_stars)} stars -- "
            f"not enough variation"
        )

    def test_stars_have_varied_dark_durations(self):
        """Stars should have different dark (off) interval durations."""
        anim = ClearNightAnimation()
        dark_durations = set()
        for star in anim.far_stars + anim.near_stars:
            dark_durations.add(star["dark_ticks"])
        # Should have at least 4 distinct dark durations
        assert len(dark_durations) >= 4, (
            f"Only {len(dark_durations)} distinct dark durations -- stars will blink too uniformly"
        )

    def test_stars_not_all_in_same_state(self):
        """At initialization, stars should be in different states (not all synchronized)."""
        anim = ClearNightAnimation()
        states = set()
        for star in anim.far_stars + anim.near_stars:
            states.add(star["state"])
        # Should have at least 2 different states at init (ideally all 4)
        assert len(states) >= 2, (
            f"All stars start in same state ({states}) -- will look synchronized"
        )

    def test_some_stars_dark_at_any_given_tick(self):
        """At any given tick, some stars should be dark (alpha=0) while others are visible.

        This is the key organic property: not all stars visible simultaneously.
        Over 30 ticks, there should be at least one tick where some stars are dark.
        """
        anim = ClearNightAnimation()
        found_mixed_frame = False
        for _ in range(30):
            bg, fg = anim.tick()
            # Count visible pixels in both layers
            visible_count = 0
            for layer in (bg, fg):
                alpha_band = layer.split()[3]
                for a in alpha_band.get_flattened_data():
                    if a > 0:
                        visible_count += 1
            # Total star count: 14 far + 6 near = 20 stars
            # If some are dark, visible_count < total star pixels at full brightness
            # With 20 stars, if all were visible, we'd see 20+ pixels (near stars have cross arms)
            # If some are dark, we see fewer
            total_stars = len(anim.far_stars) + len(anim.near_stars)
            if visible_count < total_stars:
                found_mixed_frame = True
                break
        assert found_mixed_frame, (
            "All stars appear visible every frame -- no dark intervals detected. "
            "Stars should independently go dark for organic twinkle effect."
        )

    def test_star_alpha_varies_over_time(self):
        """A single star's effective alpha should change over multiple ticks.

        This verifies the state machine is actually transitioning between
        phases rather than staying stuck.
        """
        anim = ClearNightAnimation()
        # Track alpha values for one specific near star across 50 ticks
        # We do this by reading the pixel at the star's position from the fg layer
        test_star = anim.near_stars[0]
        x, y = test_star["x"], test_star["y"]
        alphas_seen = set()
        for _ in range(50):
            bg, fg = anim.tick()
            pixel = fg.getpixel((x, y))
            alphas_seen.add(pixel[3])
        # Star should have been at multiple different alpha levels
        assert len(alphas_seen) >= 3, (
            f"Star at ({x},{y}) only produced {len(alphas_seen)} distinct alpha values "
            f"over 50 ticks: {sorted(alphas_seen)} -- twinkle not working"
        )

    def test_star_durations_re_randomize_after_cycle(self):
        """After completing a full dark->brighten->peak->dim cycle, durations should change.

        This ensures each blink cycle is different from the last.
        """
        anim = ClearNightAnimation()
        star = anim.far_stars[0]
        # Force star into a known state: start of DARK phase
        star["state"] = ClearNightAnimation._DARK
        star["timer"] = 1  # will transition to BRIGHTEN on next tick
        initial_brighten = star["brighten_ticks"]
        initial_peak = star["peak_ticks"]
        initial_dim = star["dim_ticks"]

        # Tick through: DARK(1) -> BRIGHTEN -> PEAK -> DIM -> DARK (re-randomized)
        max_ticks = 200  # safety limit
        for _ in range(max_ticks):
            anim._tick_star(star, is_near=False)
            # Check if we've re-entered DARK (meaning one full cycle completed)
            if star["state"] == ClearNightAnimation._DARK and star["timer"] == star["dark_ticks"]:
                break

        # After a full cycle, durations should have been re-randomized
        # At least one duration should be different (probabilistically near-certain)
        changed = (
            star["brighten_ticks"] != initial_brighten
            or star["peak_ticks"] != initial_peak
            or star["dim_ticks"] != initial_dim
        )
        # This could theoretically fail if random produces same values, but probability
        # is extremely low given the ranges involved
        assert changed, (
            "Star durations not re-randomized after full cycle -- "
            "each blink should be unique"
        )


class TestRainIntensity:
    """Verify rain particle count scales with precipitation amount."""

    def test_light_rain_fewer_particles(self):
        """Light rain (<1mm) should have fewer drops than default."""
        anim = RainAnimation(precipitation_mm=0.3)
        assert len(anim.far_drops) == 8
        assert len(anim.near_drops) == 4

    def test_moderate_rain_default_particles(self):
        """Moderate rain (1-3mm) should use the standard drop count."""
        anim = RainAnimation(precipitation_mm=2.0)
        assert len(anim.far_drops) == 14
        assert len(anim.near_drops) == 8

    def test_heavy_rain_more_particles(self):
        """Heavy rain (>3mm) should have dense drop count."""
        anim = RainAnimation(precipitation_mm=5.0)
        assert len(anim.far_drops) == 22
        assert len(anim.near_drops) == 14

    def test_zero_precip_uses_light(self):
        """Zero precipitation defaults to light rain particle count."""
        anim = RainAnimation(precipitation_mm=0.0)
        assert len(anim.far_drops) == 8
        assert len(anim.near_drops) == 4

    def test_boundary_moderate(self):
        """Exactly 1mm should be moderate."""
        anim = RainAnimation(precipitation_mm=1.0)
        assert len(anim.far_drops) == 14

    def test_boundary_heavy(self):
        """Just above 3mm should be heavy."""
        anim = RainAnimation(precipitation_mm=3.1)
        assert len(anim.far_drops) == 22

    def test_reset_preserves_intensity(self):
        """Reset should respawn with the same intensity-based count."""
        anim = RainAnimation(precipitation_mm=5.0)
        assert len(anim.far_drops) == 22
        anim.reset()
        assert len(anim.far_drops) == 22
        assert len(anim.near_drops) == 14

    def test_get_animation_passes_precipitation(self):
        """get_animation should pass precipitation_mm to RainAnimation."""
        anim = get_animation("rain", precipitation_mm=5.0)
        assert isinstance(anim, RainAnimation)
        assert len(anim.far_drops) == 22

    def test_thunder_passes_precipitation_to_rain(self):
        """ThunderAnimation should pass precipitation_mm to its internal rain."""
        anim = get_animation("thunder", precipitation_mm=0.5)
        assert isinstance(anim, ThunderAnimation)
        assert len(anim._rain.far_drops) == 8

    def test_heavy_rain_visible_coverage(self):
        """Heavy rain should produce more visible pixels than light rain."""
        light = RainAnimation(precipitation_mm=0.3)
        heavy = RainAnimation(precipitation_mm=6.0)
        light_pixels = 0
        heavy_pixels = 0
        for _ in range(3):
            bg, fg = light.tick()
            for layer in (bg, fg):
                alpha_band = layer.split()[3]
                light_pixels += sum(1 for a in alpha_band.get_flattened_data() if a > 0)
            bg, fg = heavy.tick()
            for layer in (bg, fg):
                alpha_band = layer.split()[3]
                heavy_pixels += sum(1 for a in alpha_band.get_flattened_data() if a > 0)
        assert heavy_pixels > light_pixels, (
            f"Heavy rain ({heavy_pixels} pixels) should have more coverage than light ({light_pixels})"
        )


class TestSunBody:
    """Verify sun body is visible in SunAnimation for visual context."""

    def test_sun_body_produces_warm_pixels_at_position(self):
        """Sun body should produce warm yellow pixels near its position."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        # Sun body is drawn in bg layer at (_SUN_X, _SUN_Y)
        sx, sy = SunAnimation._SUN_X, SunAnimation._SUN_Y
        pixel = bg.getpixel((sx, sy))
        r, g, b, a = pixel
        assert a >= 150, f"Sun body center alpha {a} too low"
        assert r > b + 50, f"Sun body not warm yellow: R={r} B={b}"

    def test_sun_body_has_glow(self):
        """Sun body should have a softer glow around the core."""
        anim = SunAnimation()
        bg, fg = anim.tick()
        sx, sy = SunAnimation._SUN_X, SunAnimation._SUN_Y
        r = SunAnimation._SUN_RADIUS
        # Check a pixel just outside the main body (in the glow)
        glow_pixel = bg.getpixel((sx - r - 1, sy))
        _, _, _, a = glow_pixel
        assert a > 0, "No glow detected around sun body"

    def test_sun_animation_still_has_rays(self):
        """Sun animation should still produce ray particles alongside the body."""
        anim = SunAnimation()
        colors = _sample_particle_rgb(anim, num_ticks=3)
        assert len(colors) > 10, f"Only {len(colors)} particles -- rays should still be active"
