# Design: Seasonal Night Mode + Layered Weather Animations

## Feature 1: Seasonal Night Mode with Real Sunset/Sunrise Times

### Problem
Night mode uses hardcoded 21:00-06:00 regardless of season. December sunset is ~16:00, June sunset ~21:00+. Brightness and animation selection (stars vs sun) should track actual darkness.

### Solution
Use the `astral` library to compute sunrise/sunset times from the user's lat/lon (already in config as `WEATHER_LAT`/`WEATHER_LON`).

### Changes

**New module `providers/sun.py`:**
- Compute sunrise, sunset, and civil twilight (sun 6 below horizon) for today's date
- Cache per-day (recompute only when date changes)
- Expose `is_dark(dt, lat, lon) -> bool` using civil twilight boundaries
- Civil twilight gives ~30min gradual transition after geometric sunset

**Modified `config.py`:**
- Replace `get_target_brightness(hour)` with `get_target_brightness(dt, lat, lon)`
- Remove `BRIGHTNESS_DIM_START`/`BRIGHTNESS_DIM_END` constants
- Calls `is_dark()` internally

**Modified `main.py`:**
- Pass `datetime.now()` + lat/lon to brightness check
- Use `is_dark()` for the `is_night` flag to `get_animation()`, replacing `not weather_data.is_day` (MET symbol suffix is less granular than real sun position)

**New dependency:**
- `astral` (add to pyproject.toml)

---

## Feature 2: Layered Weather Animations

### Problem
Weather animations play individually. Real weather involves combinations (rain + wind, heavy rain + fog, snow + wind). Intensity scaling only exists for rain; snow and fog are static.

### Solution
Add `CompositeAnimation` for layering, `WindEffect` for wind-driven particle drift, intensity scaling for all particle types, and combination rules in the animation factory.

### Changes

**Modified `WeatherData` (`weather.py`):**
- Add `wind_speed: float` (m/s) and `wind_from_direction: float` (degrees) fields
- Parse from MET API `instant.details` (already present in every response)

**New class `CompositeAnimation` (`weather_anim.py`):**
- Holds a list of WeatherAnimation instances
- `tick()` composites all sub-animations' bg layers together and fg layers together via `Image.alpha_composite()`

**New class `WindEffect` (`weather_anim.py`):**
- Modifier that adds horizontal drift to particle-based animations
- Drift magnitude proportional to `wind_speed`
- Drift direction from `wind_from_direction`
- Applied to rain drops and snow flakes by shifting x position each tick

**Intensity scaling additions:**
- `SnowAnimation`: Accept `precipitation_mm`, scale particle count (like rain)
- `FogAnimation`: Accept density parameter, more/thicker blobs when precipitation present
- `RainAnimation`: Add extreme tier (>5mm: 30+ particles, longer streaks)

**Combination rules in `get_animation()`:**
- Rain + wind_speed > 5 m/s: rain with wind drift
- Snow + wind_speed > 3 m/s: snow with wind drift
- Heavy rain (>3mm) when fog-like visibility: rain + fog overlay
- Thunder already layers rain internally; add wind if applicable

**Updated `get_animation()` signature:**
```python
def get_animation(
    weather_group: str, *,
    is_night: bool = False,
    precipitation_mm: float = 0.0,
    wind_speed: float = 0.0,
    wind_direction: float = 0.0,
) -> WeatherAnimation:
```

**Modified `main.py`:**
- Pass `wind_speed` and `wind_direction` from WeatherData to `get_animation()`
- Add wind speed change to animation swap conditions
