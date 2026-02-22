# Seasonal Night Mode + Layered Weather Animations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded night mode with astronomical sunset/sunrise calculation, and add layered/composite weather animations with wind effects and intensity scaling.

**Architecture:** Two independent features sharing a common integration point in `main.py`. Feature 1 adds a sun provider using the `astral` library. Feature 2 extends the existing animation system with `CompositeAnimation`, `WindEffect`, and per-animation intensity scaling. Both features add new fields to `WeatherData` or config and flow through the existing animation factory.

**Tech Stack:** Python 3.10+, astral (sun calculations), Pillow (animation rendering), pytest

---

### Task 1: Install astral dependency

**Files:**
- Modify: `pyproject.toml:7` (dependencies list)

**Step 1: Add astral to dependencies**

In `pyproject.toml`, add `"astral>=3.2"` to the `dependencies` list after `"python-dotenv>=1.0"`.

**Step 2: Install**

Run: `pip install astral` (or `.venv/bin/pip install astral`)

**Step 3: Verify**

Run: `.venv/bin/python -c "from astral import Observer; from astral.sun import sunrise, sunset, dawn, dusk; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add astral dependency for sunrise/sunset calculation"
```

---

### Task 2: Create sun provider with tests (TDD)

**Files:**
- Create: `src/providers/sun.py`
- Create: `tests/test_sun_provider.py`

**Step 1: Write the failing tests**

Create `tests/test_sun_provider.py`:

```python
"""Tests for the sun provider (sunrise/sunset/twilight calculation)."""

from datetime import datetime, date, timezone

import pytest

from src.providers.sun import is_dark, get_sun_times


class TestGetSunTimes:
    """Verify sun time calculation for known locations and dates."""

    def test_oslo_winter_solstice(self):
        """Oslo Dec 21: sunrise ~09:18, sunset ~15:12 UTC."""
        times = get_sun_times(59.91, 10.75, date(2026, 12, 21))
        # Dawn should be before sunrise
        assert times["dawn"] < times["sunrise"]
        # Sunset should be before dusk
        assert times["sunset"] < times["dusk"]
        # Winter: sunrise after 08:00 UTC, sunset before 16:00 UTC
        assert times["sunrise"].hour >= 8
        assert times["sunset"].hour <= 15

    def test_oslo_summer_solstice(self):
        """Oslo Jun 21: sunrise ~01:53, sunset ~20:43 UTC."""
        times = get_sun_times(59.91, 10.75, date(2026, 6, 21))
        # Summer: sunrise before 03:00 UTC, sunset after 20:00 UTC
        assert times["sunrise"].hour <= 3
        assert times["sunset"].hour >= 20

    def test_caches_per_day(self):
        """Calling twice with same date should return same object (cached)."""
        t1 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        t2 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        assert t1 is t2

    def test_different_dates_not_cached(self):
        """Different dates should produce different results."""
        t1 = get_sun_times(59.91, 10.75, date(2026, 3, 15))
        t2 = get_sun_times(59.91, 10.75, date(2026, 6, 15))
        assert t1 is not t2


class TestIsDark:
    """Verify is_dark returns correct day/night status."""

    def test_midnight_is_dark(self):
        """Midnight in Oslo in March should be dark."""
        dt = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True

    def test_noon_is_light(self):
        """Noon in Oslo in March should be light."""
        dt = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is False

    def test_uses_dusk_not_sunset(self):
        """After geometric sunset but before civil dusk should still be light.

        In Oslo on March 15, sunset is ~17:10 UTC, dusk ~17:55 UTC.
        At 17:30 UTC it's past sunset but before dusk -- should NOT be dark.
        """
        dt = datetime(2026, 3, 15, 17, 30, tzinfo=timezone.utc)
        result = is_dark(dt, 59.91, 10.75)
        # Between sunset and dusk = still light (civil twilight)
        assert result is False

    def test_after_dusk_is_dark(self):
        """Well after dusk should be dark."""
        dt = datetime(2026, 3, 15, 20, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True

    def test_before_dawn_is_dark(self):
        """Before dawn should be dark."""
        dt = datetime(2026, 3, 15, 4, 0, tzinfo=timezone.utc)
        assert is_dark(dt, 59.91, 10.75) is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sun_provider.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

Create `src/providers/sun.py`:

```python
"""Sun position provider using the astral library.

Computes sunrise, sunset, civil dawn, and civil dusk times for a given
location and date. Caches results per-day since sun times only change
once per calendar day.
"""

from datetime import date, datetime, timezone

from astral import Observer
from astral.sun import dawn, dusk, sunrise, sunset


# Cache: (lat, lon, date) -> sun times dict
_cache_key: tuple[float, float, date] | None = None
_cache_value: dict[str, datetime] | None = None


def get_sun_times(lat: float, lon: float, d: date) -> dict[str, datetime]:
    """Compute sunrise, sunset, dawn, and dusk for a location and date.

    Results are cached per (lat, lon, date) tuple since sun times only
    change once per calendar day.

    Args:
        lat: Latitude in decimal degrees (positive = north).
        lon: Longitude in decimal degrees (positive = east).
        d: Date to compute sun times for.

    Returns:
        Dictionary with keys "dawn", "sunrise", "sunset", "dusk",
        each mapping to a timezone-aware UTC datetime.
    """
    global _cache_key, _cache_value

    key = (lat, lon, d)
    if _cache_key == key and _cache_value is not None:
        return _cache_value

    observer = Observer(latitude=lat, longitude=lon)
    times = {
        "dawn": dawn(observer, date=d, tzinfo=timezone.utc),
        "sunrise": sunrise(observer, date=d, tzinfo=timezone.utc),
        "sunset": sunset(observer, date=d, tzinfo=timezone.utc),
        "dusk": dusk(observer, date=d, tzinfo=timezone.utc),
    }
    _cache_key = key
    _cache_value = times
    return times


def is_dark(dt: datetime, lat: float, lon: float) -> bool:
    """Check if it's dark at the given time and location.

    Uses civil twilight boundaries (dawn/dusk) rather than geometric
    sunrise/sunset, giving a ~30-minute buffer after sunset where
    there's still usable light.

    Args:
        dt: Timezone-aware datetime to check.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        True if the time is before civil dawn or after civil dusk.
    """
    times = get_sun_times(lat, lon, dt.date())
    return dt < times["dawn"] or dt > times["dusk"]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sun_provider.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/providers/sun.py tests/test_sun_provider.py
git commit -m "feat: add sun provider with sunrise/sunset/twilight calculation"
```

---

### Task 3: Wire sun provider into brightness control

**Files:**
- Modify: `src/config.py:26-46` (replace hardcoded brightness schedule)
- Modify: `src/main.py:223` (update brightness call site)

**Step 1: Update config.py**

Replace `get_target_brightness()` to use the sun provider. Remove `BRIGHTNESS_DIM_START` and `BRIGHTNESS_DIM_END`. The new function takes a `datetime` and lat/lon:

```python
def get_target_brightness(dt: datetime, lat: float, lon: float) -> int:
    """Return target brightness based on astronomical darkness.

    Uses civil twilight (sun 6 deg below horizon) from the astral library
    instead of hardcoded hours.

    Args:
        dt: Current timezone-aware datetime.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Target brightness percentage (0-100).
    """
    from src.providers.sun import is_dark
    if is_dark(dt, lat, lon):
        return BRIGHTNESS_NIGHT
    return BRIGHTNESS_DAY
```

Add `from datetime import datetime` to imports if not already present.

**Step 2: Update main.py brightness call**

In `main_loop()`, change the brightness check from:
```python
target_brightness = get_target_brightness(now.hour)
```
to:
```python
from datetime import timezone
now_utc = now.astimezone(timezone.utc)
target_brightness = get_target_brightness(now_utc, WEATHER_LAT, WEATHER_LON)
```

Also add import of `WEATHER_LAT, WEATHER_LON` (already imported).

**Step 3: Update main.py is_night flag**

Replace the `is_night = not weather_data.is_day` logic with sun-based calculation. In the weather refresh block, after getting weather_data, compute:

```python
from src.providers.sun import is_dark
is_night = is_dark(now_utc, WEATHER_LAT, WEATHER_LON)
```

This replaces the MET symbol_code suffix (`_day`/`_night`) with actual sun position.

**Step 4: Run existing tests**

Run: `pytest tests/ -v`
Expected: All existing tests pass (config tests may need updating if any test `get_target_brightness` directly)

**Step 5: Commit**

```bash
git add src/config.py src/main.py
git commit -m "feat: wire sun provider into brightness and animation day/night"
```

---

### Task 4: Add wind data to WeatherData (TDD)

**Files:**
- Modify: `src/providers/weather.py:24-32` (WeatherData dataclass)
- Modify: `src/providers/weather.py:59-70` (_parse_current)
- Modify: `tests/test_weather_provider.py`

**Step 1: Write failing tests**

Add to `tests/test_weather_provider.py`:

Update `_make_entry` to include wind data:

```python
def _make_entry(time_str: str, temp: float, symbol: str = "cloudy",
                precip: float = 0.0, high6h: float | None = None,
                low6h: float | None = None,
                wind_speed: float = 3.0, wind_direction: float = 180.0) -> dict:
    """Build a single MET API timeseries entry for testing."""
    entry: dict = {
        "time": time_str,
        "data": {
            "instant": {
                "details": {
                    "air_temperature": temp,
                    "wind_speed": wind_speed,
                    "wind_from_direction": wind_direction,
                }
            },
            "next_1_hours": {
                "summary": {"symbol_code": symbol},
                "details": {"precipitation_amount": precip},
            },
        },
    }
    if high6h is not None or low6h is not None:
        entry["data"]["next_6_hours"] = {
            "details": {
                "air_temperature_max": high6h if high6h is not None else 0.0,
                "air_temperature_min": low6h if low6h is not None else 0.0,
            }
        }
    return entry
```

Add new test class:

```python
class TestWindData:
    def test_parse_current_includes_wind(self):
        ts = [_make_entry(f"{_today_str()}T12:00:00Z", 5.0, "rain_day", 2.0,
                          wind_speed=8.5, wind_direction=270.0)]
        result = _parse_current(ts)
        assert result["wind_speed"] == 8.5
        assert result["wind_from_direction"] == 270.0

    def test_weather_data_has_wind_fields(self):
        dt = datetime(2026, 2, 20, 14, 30)
        wd = WeatherData(
            temperature=5.0, symbol_code="rain_day", high_temp=8.0,
            low_temp=1.0, precipitation_mm=2.0, is_day=True,
            wind_speed=8.5, wind_from_direction=270.0,
        )
        assert wd.wind_speed == 8.5
        assert wd.wind_from_direction == 270.0

    def test_wind_defaults_to_zero(self):
        """Wind fields should default to 0 when not provided."""
        wd = WeatherData(
            temperature=5.0, symbol_code="rain", high_temp=8.0,
            low_temp=1.0, precipitation_mm=0.0, is_day=True,
        )
        assert wd.wind_speed == 0.0
        assert wd.wind_from_direction == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_weather_provider.py::TestWindData -v`
Expected: FAIL

**Step 3: Implement wind data extraction**

In `src/providers/weather.py`:

1. Add fields to `WeatherData`:
```python
@dataclass
class WeatherData:
    temperature: float
    symbol_code: str
    high_temp: float
    low_temp: float
    precipitation_mm: float
    is_day: bool
    wind_speed: float = 0.0
    wind_from_direction: float = 0.0
```

2. Update `_parse_current()` to extract wind:
```python
def _parse_current(timeseries: list[dict]) -> dict:
    entry = timeseries[0]
    instant = entry["data"]["instant"]["details"]
    next_1h = entry["data"].get("next_1_hours", {})
    symbol_code = next_1h.get("summary", {}).get("symbol_code", "cloudy")
    return {
        "temperature": instant["air_temperature"],
        "symbol_code": symbol_code,
        "precipitation_mm": next_1h.get("details", {}).get("precipitation_amount", 0.0),
        "is_day": _parse_is_day(symbol_code),
        "wind_speed": instant.get("wind_speed", 0.0),
        "wind_from_direction": instant.get("wind_from_direction", 0.0),
    }
```

3. Update `fetch_weather()` to pass wind to `WeatherData`:
```python
return WeatherData(
    temperature=current["temperature"],
    symbol_code=current["symbol_code"],
    high_temp=high,
    low_temp=low,
    precipitation_mm=current["precipitation_mm"],
    is_day=current["is_day"],
    wind_speed=current["wind_speed"],
    wind_from_direction=current["wind_from_direction"],
)
```

**Step 4: Run tests**

Run: `pytest tests/test_weather_provider.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/providers/weather.py tests/test_weather_provider.py
git commit -m "feat: extract wind speed and direction from MET API"
```

---

### Task 5: Add snow intensity scaling (TDD)

**Files:**
- Modify: `src/display/weather_anim.py` (SnowAnimation class)
- Modify: `tests/test_weather_anim.py`

**Step 1: Write failing tests**

Add to `tests/test_weather_anim.py`:

```python
class TestSnowIntensity:
    """Verify snow particle count scales with precipitation amount."""

    def test_light_snow_fewer_particles(self):
        anim = SnowAnimation(precipitation_mm=0.3)
        assert len(anim.far_flakes) == 6
        assert len(anim.near_flakes) == 3

    def test_moderate_snow_default_particles(self):
        anim = SnowAnimation(precipitation_mm=2.0)
        assert len(anim.far_flakes) == 10
        assert len(anim.near_flakes) == 6

    def test_heavy_snow_more_particles(self):
        anim = SnowAnimation(precipitation_mm=4.0)
        assert len(anim.far_flakes) == 16
        assert len(anim.near_flakes) == 10

    def test_default_is_moderate(self):
        """No precipitation arg defaults to moderate (backward compat)."""
        anim = SnowAnimation()
        assert len(anim.far_flakes) == 10
        assert len(anim.near_flakes) == 6

    def test_reset_preserves_intensity(self):
        anim = SnowAnimation(precipitation_mm=4.0)
        assert len(anim.far_flakes) == 16
        anim.reset()
        assert len(anim.far_flakes) == 16
        assert len(anim.near_flakes) == 10
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_weather_anim.py::TestSnowIntensity -v`
Expected: FAIL (SnowAnimation doesn't accept precipitation_mm)

**Step 3: Implement**

Update `SnowAnimation.__init__` to accept `precipitation_mm` and scale particle count:

```python
class SnowAnimation(WeatherAnimation):
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
        if precipitation_mm < 1.0:
            return 6, 3
        elif precipitation_mm <= 3.0:
            return 10, 6
        else:
            return 16, 10
```

Update `reset()`:
```python
    def reset(self) -> None:
        self.far_flakes.clear()
        self.near_flakes.clear()
        self._spawn_far(self._far_count)
        self._spawn_near(self._near_count)
```

**Step 4: Run tests**

Run: `pytest tests/test_weather_anim.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/display/weather_anim.py tests/test_weather_anim.py
git commit -m "feat: add precipitation-based intensity scaling to snow animation"
```

---

### Task 6: Add extreme rain tier (TDD)

**Files:**
- Modify: `src/display/weather_anim.py` (RainAnimation._particle_counts)
- Modify: `tests/test_weather_anim.py`

**Step 1: Write failing tests**

Add to `TestRainIntensity` in `tests/test_weather_anim.py`:

```python
    def test_extreme_rain_even_more_particles(self):
        """Extreme rain (>5mm) should have maximum density."""
        anim = RainAnimation(precipitation_mm=8.0)
        assert len(anim.far_drops) == 30
        assert len(anim.near_drops) == 18
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_weather_anim.py::TestRainIntensity::test_extreme_rain_even_more_particles -v`
Expected: FAIL (returns 22, 14 instead of 30, 18)

**Step 3: Implement**

Update `RainAnimation._particle_counts`:

```python
    @staticmethod
    def _particle_counts(precipitation_mm: float) -> tuple[int, int]:
        if precipitation_mm < 1.0:
            return 8, 4
        elif precipitation_mm <= 3.0:
            return 14, 8
        elif precipitation_mm <= 5.0:
            return 22, 14
        else:
            return 30, 18
```

**Step 4: Run tests**

Run: `pytest tests/test_weather_anim.py::TestRainIntensity -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/display/weather_anim.py tests/test_weather_anim.py
git commit -m "feat: add extreme rain intensity tier (>5mm)"
```

---

### Task 7: Add CompositeAnimation (TDD)

**Files:**
- Modify: `src/display/weather_anim.py` (new CompositeAnimation class)
- Modify: `tests/test_weather_anim.py`

**Step 1: Write failing tests**

Add to `tests/test_weather_anim.py`:

```python
from src.display.weather_anim import CompositeAnimation


class TestCompositeAnimation:
    """Verify CompositeAnimation blends multiple animations."""

    def test_single_animation_passthrough(self):
        """Single animation should produce same output as standalone."""
        rain = RainAnimation(precipitation_mm=2.0)
        comp = CompositeAnimation([rain])
        bg, fg = comp.tick()
        assert bg.size == (64, 24)
        assert bg.mode == "RGBA"
        assert fg.size == (64, 24)

    def test_two_animations_produce_visible_output(self):
        """Composite of rain + fog should have pixels from both."""
        rain = RainAnimation(precipitation_mm=3.0)
        fog = FogAnimation()
        comp = CompositeAnimation([rain, fog])
        # Tick a few times to let particles settle
        for _ in range(5):
            bg, fg = comp.tick()
        # Should have non-transparent pixels
        bg_alpha = bg.split()[3]
        fg_alpha = fg.split()[3]
        bg_pixels = sum(1 for a in bg_alpha.get_flattened_data() if a > 0)
        fg_pixels = sum(1 for a in fg_alpha.get_flattened_data() if a > 0)
        assert bg_pixels > 0, "Composite bg has no visible pixels"
        assert fg_pixels > 0, "Composite fg has no visible pixels"

    def test_reset_resets_all_children(self):
        """Reset should propagate to all child animations."""
        rain = RainAnimation(precipitation_mm=2.0)
        snow = SnowAnimation(precipitation_mm=2.0)
        comp = CompositeAnimation([rain, snow])
        # Tick to advance state
        for _ in range(10):
            comp.tick()
        comp.reset()
        # After reset, particles should be re-spawned
        assert len(rain.far_drops) == 14
        assert len(snow.far_flakes) == 10

    def test_empty_animations_returns_empty_layers(self):
        """Composite with no animations should return transparent layers."""
        comp = CompositeAnimation([])
        bg, fg = comp.tick()
        alpha = bg.split()[3]
        assert max(alpha.get_flattened_data()) == 0
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_weather_anim.py::TestCompositeAnimation -v`
Expected: FAIL (import error)

**Step 3: Implement**

Add to `src/display/weather_anim.py`:

```python
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
```

**Step 4: Run tests**

Run: `pytest tests/test_weather_anim.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/display/weather_anim.py tests/test_weather_anim.py
git commit -m "feat: add CompositeAnimation for layering multiple weather effects"
```

---

### Task 8: Add WindEffect modifier (TDD)

**Files:**
- Modify: `src/display/weather_anim.py` (new WindEffect class)
- Modify: `tests/test_weather_anim.py`

**Step 1: Write failing tests**

Add to `tests/test_weather_anim.py`:

```python
from src.display.weather_anim import WindEffect


class TestWindEffect:
    """Verify WindEffect adds horizontal drift to particle animations."""

    def test_wind_shifts_rain_drops(self):
        """Rain drops should drift horizontally with wind."""
        rain = RainAnimation(precipitation_mm=2.0)
        wind = WindEffect(rain, wind_speed=10.0, wind_direction=270.0)
        # Record initial x positions
        initial_x = [d[0] for d in rain.far_drops]
        # Tick several times
        for _ in range(5):
            wind.tick()
        # Drops should have moved -- at least some x positions changed
        current_x = [d[0] for d in rain.far_drops]
        assert initial_x != current_x, "Wind had no effect on drop positions"

    def test_no_wind_no_drift(self):
        """Zero wind speed should not add horizontal drift."""
        rain = RainAnimation(precipitation_mm=2.0)
        wind = WindEffect(rain, wind_speed=0.0, wind_direction=270.0)
        # Record initial state
        initial_x = [d[0] for d in rain.far_drops[:]]
        # Tick once -- rain naturally moves a bit, but wind adds no extra
        bg1, fg1 = wind.tick()
        assert bg1.size == (64, 24)
        assert bg1.mode == "RGBA"

    def test_wind_returns_two_layers(self):
        """WindEffect should return proper (bg, fg) tuple."""
        rain = RainAnimation(precipitation_mm=2.0)
        wind = WindEffect(rain, wind_speed=8.0, wind_direction=180.0)
        bg, fg = wind.tick()
        assert bg.size == (64, 24) and bg.mode == "RGBA"
        assert fg.size == (64, 24) and fg.mode == "RGBA"

    def test_wind_direction_affects_drift_sign(self):
        """Wind from west (270) should drift east (positive x)."""
        rain1 = RainAnimation(precipitation_mm=2.0)
        wind_west = WindEffect(rain1, wind_speed=10.0, wind_direction=270.0)
        assert wind_west._drift_per_tick > 0  # westerly wind pushes east

        rain2 = RainAnimation(precipitation_mm=2.0)
        wind_east = WindEffect(rain2, wind_speed=10.0, wind_direction=90.0)
        assert wind_east._drift_per_tick < 0  # easterly wind pushes west

    def test_reset_delegates(self):
        """Reset should delegate to inner animation."""
        rain = RainAnimation(precipitation_mm=5.0)
        wind = WindEffect(rain, wind_speed=8.0, wind_direction=270.0)
        for _ in range(10):
            wind.tick()
        wind.reset()
        assert len(rain.far_drops) == 22
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_weather_anim.py::TestWindEffect -v`
Expected: FAIL (import error)

**Step 3: Implement**

Add to `src/display/weather_anim.py`:

```python
import math


class WindEffect(WeatherAnimation):
    """Wraps a particle-based animation and adds wind-driven horizontal drift.

    Wind direction is meteorological: 270 = from west (blows east).
    Drift magnitude scales with wind_speed (m/s). At 10 m/s, drift is
    ~2 pixels per tick. Affects all particle lists found on the inner
    animation (far_drops, near_drops, far_flakes, near_flakes).

    Args:
        inner: The animation to wrap.
        wind_speed: Wind speed in m/s.
        wind_direction: Meteorological wind direction in degrees
                        (direction wind is blowing FROM).
    """

    def __init__(
        self,
        inner: WeatherAnimation,
        wind_speed: float = 0.0,
        wind_direction: float = 0.0,
    ) -> None:
        super().__init__(inner.width, inner.height)
        self.inner = inner
        self.wind_speed = wind_speed
        # Convert meteorological direction to drift: wind FROM west (270) blows east (+x)
        # sin(270) = -1, so negate to get +x drift for westerly wind
        wind_rad = math.radians(wind_direction)
        self._drift_per_tick = -math.sin(wind_rad) * (wind_speed / 5.0)

    def tick(self) -> tuple[Image.Image, Image.Image]:
        # Apply horizontal drift to all known particle lists
        drift = self._drift_per_tick
        for attr in ("far_drops", "near_drops", "far_flakes", "near_flakes"):
            particles = getattr(self.inner, attr, None)
            if particles:
                for p in particles:
                    p[0] += drift
                    # Wrap around horizontally
                    if p[0] >= self.width:
                        p[0] -= self.width
                    elif p[0] < 0:
                        p[0] += self.width
        return self.inner.tick()

    def reset(self) -> None:
        self.inner.reset()
```

**Step 4: Run tests**

Run: `pytest tests/test_weather_anim.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/display/weather_anim.py tests/test_weather_anim.py
git commit -m "feat: add WindEffect modifier for horizontal particle drift"
```

---

### Task 9: Update get_animation factory with combos and wind (TDD)

**Files:**
- Modify: `src/display/weather_anim.py` (get_animation function)
- Modify: `tests/test_weather_anim.py`

**Step 1: Write failing tests**

Add to `tests/test_weather_anim.py`:

```python
class TestAnimationCombos:
    """Verify get_animation produces composite animations for weather combos."""

    def test_rain_with_strong_wind_returns_wind_effect(self):
        """Rain + wind >5 m/s should wrap rain in WindEffect."""
        anim = get_animation("rain", precipitation_mm=3.0, wind_speed=8.0, wind_direction=270.0)
        assert isinstance(anim, WindEffect)
        assert isinstance(anim.inner, RainAnimation)

    def test_rain_with_light_wind_no_wind_effect(self):
        """Rain + wind <5 m/s should be plain rain."""
        anim = get_animation("rain", precipitation_mm=3.0, wind_speed=3.0)
        assert isinstance(anim, RainAnimation)

    def test_snow_with_wind_returns_wind_effect(self):
        """Snow + wind >3 m/s should wrap snow in WindEffect."""
        anim = get_animation("snow", precipitation_mm=2.0, wind_speed=5.0, wind_direction=180.0)
        assert isinstance(anim, WindEffect)
        assert isinstance(anim.inner, SnowAnimation)

    def test_snow_passes_precipitation(self):
        """Snow animation should receive precipitation_mm."""
        anim = get_animation("snow", precipitation_mm=4.0)
        assert isinstance(anim, SnowAnimation)
        assert len(anim.far_flakes) == 16  # heavy snow tier

    def test_heavy_rain_with_fog_returns_composite(self):
        """Heavy rain (>3mm) should add fog overlay via CompositeAnimation."""
        anim = get_animation("rain", precipitation_mm=5.0)
        assert isinstance(anim, CompositeAnimation)
        # Should contain rain and fog
        types = [type(a).__name__ for a in anim.animations]
        assert "RainAnimation" in types
        assert "FogAnimation" in types

    def test_heavy_rain_fog_with_wind_wraps_composite(self):
        """Heavy rain + fog + wind should wrap the composite in WindEffect."""
        anim = get_animation("rain", precipitation_mm=6.0, wind_speed=8.0, wind_direction=270.0)
        assert isinstance(anim, WindEffect)
        assert isinstance(anim.inner, CompositeAnimation)

    def test_thunder_with_wind(self):
        """Thunder + strong wind should wrap in WindEffect."""
        anim = get_animation("thunder", precipitation_mm=5.0, wind_speed=8.0, wind_direction=270.0)
        assert isinstance(anim, WindEffect)
        assert isinstance(anim.inner, ThunderAnimation)

    def test_clear_day_unaffected_by_wind(self):
        """Sun animation should not be affected by wind."""
        anim = get_animation("clear", wind_speed=15.0)
        assert isinstance(anim, SunAnimation)

    def test_fog_unaffected_by_wind(self):
        """Fog animation should not be wrapped in wind (fog is ground-level)."""
        anim = get_animation("fog", wind_speed=10.0)
        assert isinstance(anim, FogAnimation)

    def test_backward_compat_no_wind_params(self):
        """Calling get_animation without wind params should work as before."""
        anim = get_animation("rain", precipitation_mm=2.0)
        assert isinstance(anim, RainAnimation)
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_weather_anim.py::TestAnimationCombos -v`
Expected: FAIL (get_animation doesn't accept wind params)

**Step 3: Implement**

Replace `get_animation()` in `src/display/weather_anim.py`:

```python
# Wind thresholds (m/s)
_WIND_THRESHOLD_RAIN = 5.0
_WIND_THRESHOLD_SNOW = 3.0

# Precipitation threshold for fog overlay on heavy rain
_FOG_OVERLAY_PRECIP = 3.0


def get_animation(
    weather_group: str,
    *,
    is_night: bool = False,
    precipitation_mm: float = 0.0,
    wind_speed: float = 0.0,
    wind_direction: float = 0.0,
) -> WeatherAnimation:
    """Get an animation instance for the given weather conditions.

    Builds composite animations for intense conditions:
    - Rain/snow with strong wind: wrapped in WindEffect
    - Heavy rain (>3mm): layered with fog overlay
    - Thunder: internal rain + lightning, optionally with wind

    Args:
        weather_group: Weather group name (clear, rain, snow, etc.).
        is_night: True if it's nighttime.
        precipitation_mm: Precipitation amount in mm/h.
        wind_speed: Wind speed in m/s.
        wind_direction: Meteorological wind direction in degrees.

    Returns:
        A WeatherAnimation (possibly CompositeAnimation or WindEffect).
    """
    # Night overrides for clear/partcloud
    if is_night:
        cls = _NIGHT_ANIMATION_MAP.get(weather_group)
        if cls is not None:
            return cls()

    cls = _ANIMATION_MAP.get(weather_group, CloudAnimation)

    # Build the base animation
    if cls is RainAnimation:
        base = RainAnimation(precipitation_mm=precipitation_mm)
        # Heavy rain gets fog overlay
        if precipitation_mm > _FOG_OVERLAY_PRECIP:
            base = CompositeAnimation([base, FogAnimation()])
    elif cls is ThunderAnimation:
        base = ThunderAnimation(precipitation_mm=precipitation_mm)
    elif cls is SnowAnimation:
        base = SnowAnimation(precipitation_mm=precipitation_mm)
    else:
        base = cls()

    # Apply wind effect to particle-based animations
    wind_applicable = cls in (RainAnimation, SnowAnimation, ThunderAnimation)
    if wind_applicable and wind_speed > 0:
        threshold = _WIND_THRESHOLD_SNOW if cls is SnowAnimation else _WIND_THRESHOLD_RAIN
        if wind_speed > threshold:
            base = WindEffect(base, wind_speed=wind_speed, wind_direction=wind_direction)

    return base
```

**Step 4: Run all tests**

Run: `pytest tests/test_weather_anim.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/display/weather_anim.py tests/test_weather_anim.py
git commit -m "feat: add weather animation combos with wind effects and fog overlay"
```

---

### Task 10: Wire wind data into main loop

**Files:**
- Modify: `src/main.py` (pass wind to get_animation, add wind change detection)
- Modify: `src/main.py` (update test weather map)

**Step 1: Update test weather map**

In `main_loop()`, update the `test_weather_map` entries to include wind data:

```python
test_weather_map = {
    "clear": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True, wind_speed=2.0, wind_from_direction=180.0),
    "rain": WeatherData(temperature=30, symbol_code="rain_day", high_temp=32, low_temp=22, precipitation_mm=5.0, is_day=True, wind_speed=8.0, wind_from_direction=270.0),
    "snow": WeatherData(temperature=30, symbol_code="snow_day", high_temp=32, low_temp=22, precipitation_mm=2.0, is_day=True, wind_speed=5.0, wind_from_direction=200.0),
    "fog": WeatherData(temperature=30, symbol_code="fog", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
    "cloudy": WeatherData(temperature=30, symbol_code="cloudy", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
    "sun": WeatherData(temperature=30, symbol_code="clearsky_day", high_temp=32, low_temp=22, precipitation_mm=0.0, is_day=True),
    "thunder": WeatherData(temperature=30, symbol_code="rainandthunder_day", high_temp=32, low_temp=22, precipitation_mm=8.0, is_day=True, wind_speed=12.0, wind_from_direction=250.0),
}
```

**Step 2: Pass wind to get_animation**

In both the test weather block and the real weather block, update calls to `get_animation()`:

```python
weather_anim = get_animation(
    new_group,
    is_night=is_night,
    precipitation_mm=precip,
    wind_speed=weather_data.wind_speed,
    wind_direction=weather_data.wind_from_direction,
)
```

**Step 3: Add wind change detection**

Add a `_wind_category` function near `_precip_category`:

```python
def _wind_category(speed: float) -> str:
    """Classify wind speed for animation switching."""
    if speed < 3.0:
        return "calm"
    elif speed <= 5.0:
        return "moderate"
    return "strong"
```

Add tracking variable `last_wind_speed: float = 0.0` alongside `last_precip_mm`.

Update the animation swap condition:

```python
wind_changed = _wind_category(weather_data.wind_speed) != _wind_category(last_wind_speed)
if new_group != last_weather_group or is_night != last_weather_night or precip_changed or wind_changed:
    weather_anim = get_animation(...)
    last_wind_speed = weather_data.wind_speed
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: wire wind data into animation factory with wind change detection"
```

---

### Task 11: Update DisplayState test fixtures for wind fields

**Files:**
- Modify: `tests/test_weather_provider.py` (update WeatherData fixtures that don't include wind)

**Step 1: Fix any test fixtures**

Review all `WeatherData(...)` constructor calls in existing tests. The new `wind_speed` and `wind_from_direction` fields have defaults of `0.0`, so existing tests should still pass without changes. Run the full suite to verify.

Run: `pytest tests/ -v`

If any test fails due to the new fields, add the default values.

**Step 2: Commit (only if changes needed)**

```bash
git add tests/
git commit -m "test: update fixtures for wind data fields"
```

---

### Task 12: Run full test suite and visual check

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 2: Visual smoke test**

Run: `TEST_WEATHER=rain .venv/bin/python src/main.py --simulated --save-frame`
Verify: Rain with wind drift visible, fog overlay on heavy rain.

Run: `TEST_WEATHER=snow .venv/bin/python src/main.py --simulated --save-frame`
Verify: Snow with wind drift visible.

Run: `TEST_WEATHER=thunder .venv/bin/python src/main.py --simulated --save-frame`
Verify: Thunder with rain + lightning + wind.

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete seasonal night mode and layered weather animations"
```
