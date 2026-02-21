# Phase 3: Weather - Research

**Researched:** 2026-02-20
**Domain:** Yr/MET Norway Weather API, pixel art rendering, animated backgrounds
**Confidence:** HIGH

## Summary

Phase 3 adds live weather data from MET Norway's Locationforecast 2.0 API to the 64x20 weather zone. The API is free, well-documented, and returns JSON with current temperature, weather symbol codes, and precipitation data -- exactly what we need. No Python wrapper library is required; plain `requests` with proper User-Agent and If-Modified-Since caching is the standard approach (matches our existing bus provider pattern).

The weather zone combines animated backgrounds (rain, sun rays, clouds) with text overlay for temperatures. A weather condition icon goes next to the clock in the clock zone. The main complexity is (1) mapping ~50 MET symbol codes to a manageable set of pixel art icons and (2) implementing lightweight frame-based animations that don't overwhelm the 64x64 render pipeline.

**Primary recommendation:** Use `requests` directly against `api.met.no/weatherapi/locationforecast/2.0/compact` with a 10-minute refresh interval, map symbol codes to ~8 icon groups, and drive animations from the main loop tick rather than independent timers.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Weather condition icon goes to the RIGHT of the clock digits in the clock zone (not in the weather zone)
- Icons should have day/night variants (sun during day, moon at night, etc.)
- The weather zone below becomes text-only for temperature data and rain info
- The weather zone (64x20) gets animated background effects based on current conditions
- Raindrops falling when raining, sun rays when sunny, cloud drift when foggy/overcast, etc.
- Animation drives more frequent frame updates for the weather zone
- Text (temperature, high/low) renders on top of the animation
- No degree symbol or "C" -- just the number (e.g., "12" not "12 deg")
- Negative temperatures: use blue text color instead of a minus sign -- saves pixel space
- Positive temperatures: standard color (white or warm tone -- Claude's discretion)

### Claude's Discretion
- Zone layout arrangement within 64x20 (icon-left vs stacked vs other)
- Font sizes for temperature text (small 5x8 vs tiny 4x6)
- Weather icon set size (basic ~6 or extended ~10+, based on Yr weather codes)
- Icon creation approach (pixel arrays in code vs PNG sprites)
- Animation subtlety level (ambient vs active)
- Color scheme for weather zone text
- API refresh interval (based on Yr/MET API terms)
- Fallback behavior when Yr is unreachable
- Whether to distinguish "raining now" vs "rain expected later"
- Rain indicator: whether to show timing ("rain in 2h") or just presence

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WTHR-01 | Current temperature (deg C) from Yr/MET | Locationforecast 2.0 `air_temperature` field in `instant.details` -- returns Celsius directly |
| WTHR-02 | Weather icon as pixel art sprite | MET `symbol_code` in `next_1_hours.summary` maps to ~50 codes; group into ~8 pixel art icons with day/night variants |
| WTHR-03 | Today's high/low temperature | `next_6_hours.details` has `air_temperature_max` and `air_temperature_min`; aggregate across today's timeseries entries |
| WTHR-04 | Rain expected indicator | `next_1_hours.details.precipitation_amount` (mm) and `probability_of_precipitation` (%) available; animated rain background doubles as indicator |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | (already installed) | HTTP client for MET API | Already used by bus provider; consistent pattern |
| Pillow/PIL | (already installed) | Render weather zone, icons, animations | Already the project's render engine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none needed) | - | - | No additional dependencies required |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw requests | metno-locationforecast PyPI package | Adds dependency for a simple GET; we only need one endpoint, raw requests is simpler and matches bus provider pattern |
| Raw requests | yr-weather PyPI package | Same -- extra dependency for minimal value |

**Installation:**
No new packages needed. `requests` and `Pillow` already in the project.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── providers/
│   ├── weather.py          # MET API client (fetch + parse + cache)
│   └── bus.py              # Existing bus provider (pattern to follow)
├── display/
│   ├── state.py            # Add weather fields to DisplayState
│   ├── renderer.py         # Add weather zone + clock icon rendering
│   ├── weather_icons.py    # Pixel art icon definitions (numpy-style arrays or PIL drawing)
│   ├── weather_anim.py     # Animation frame generators (rain, sun, clouds, etc.)
│   └── layout.py           # Add weather color constants
├── config.py               # Add weather config constants
└── main.py                 # Add weather fetch cycle + animation tick
```

### Pattern 1: Provider Pattern (match bus.py)
**What:** Weather provider follows the same fetch/parse/safe-wrapper structure as bus.py
**When to use:** All external data providers
**Example:**
```python
# src/providers/weather.py -- mirrors bus.py structure

@dataclass
class WeatherData:
    temperature: float           # current temp in Celsius
    symbol_code: str             # MET symbol code, e.g. "partlycloudy_day"
    high_temp: float             # today's forecast high
    low_temp: float              # today's forecast low
    precipitation_mm: float      # next 1h precipitation amount
    precipitation_prob: float    # probability of precipitation (%)
    is_day: bool                 # derived from symbol_code suffix

def fetch_weather(lat: float, lon: float) -> WeatherData:
    """Fetch from MET API, parse timeseries, return structured data."""
    ...

def fetch_weather_safe(lat: float, lon: float) -> WeatherData | None:
    """Wrap fetch_weather with error handling; return None on failure."""
    ...
```

### Pattern 2: Animation Frame Generator
**What:** Stateful animation objects that produce overlay images on each tick
**When to use:** Weather zone animated backgrounds
**Example:**
```python
# src/display/weather_anim.py

class WeatherAnimation:
    """Base class for weather background animations."""
    def tick(self) -> Image.Image:
        """Return next animation frame as a 64x20 RGBA image."""
        ...

class RainAnimation(WeatherAnimation):
    """Falling raindrop particles."""
    ...

class SunAnimation(WeatherAnimation):
    """Subtle sun ray sweep."""
    ...
```

### Pattern 3: DisplayState Extension
**What:** Add weather fields to existing DisplayState dataclass
**When to use:** Extending state with new data sources
**Example:**
```python
# Extend DisplayState with weather fields (same pattern as bus_direction1/2)
@dataclass
class DisplayState:
    time_str: str
    date_str: str
    bus_direction1: tuple[int, ...] | None = None
    bus_direction2: tuple[int, ...] | None = None
    # New weather fields
    weather_temp: int | None = None          # current temp, rounded
    weather_symbol: str | None = None        # MET symbol_code
    weather_high: int | None = None          # today's high
    weather_low: int | None = None           # today's low
    weather_precip_mm: float | None = None   # next 1h precipitation
    weather_is_day: bool = True              # day/night for icon variant
```

### Anti-Patterns to Avoid
- **Independent animation thread:** Don't spawn threads for animation. Drive from the main loop tick (sleep interval becomes shorter when animations active).
- **Full icon PNG sprites from disk:** On a 64x64 display, weather icons are 8-12px. Drawing them programmatically in PIL is simpler and more maintainable than managing sprite files.
- **Polling MET API every second:** MET data updates every ~10 minutes. Cache locally, use If-Modified-Since.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symbol code to icon mapping | Custom weather interpretation logic | Direct symbol_code grouping from MET API | MET already classifies weather into ~50 codes; just group them |
| Day/night detection | Custom sunrise/sunset calculation | symbol_code suffix (`_day`/`_night`) from MET API | MET API already includes day/night variant in symbol_code |
| HTTP caching | Custom cache-control parsing | If-Modified-Since header + Last-Modified response | Standard HTTP conditional request; MET API fully supports it |
| Temperature rounding | Complex rounding logic | Python `round()` on float | API returns float with 1 decimal; round to int for display |

**Key insight:** MET API does the heavy lifting. The symbol_code already encodes weather condition + day/night. Precipitation data is pre-computed. We just need to fetch, parse, and render.

## Common Pitfalls

### Pitfall 1: Missing or Generic User-Agent
**What goes wrong:** API returns 403 Forbidden
**Why it happens:** MET requires identifying User-Agent since 2020; generic headers are blocked
**How to avoid:** Set `User-Agent: divoom-hub/0.1 github.com/jdl/divoom-hub` (or similar with contact info)
**Warning signs:** 403 responses during development

### Pitfall 2: Hammering the API
**What goes wrong:** 429 rate limiting, potential IP ban
**Why it happens:** Fetching on every render loop iteration instead of caching
**How to avoid:** 10-minute refresh interval; use If-Modified-Since header; cache response locally
**Warning signs:** 429 responses, "please cache" warnings in response headers

### Pitfall 3: Incorrect High/Low Temperature Calculation
**What goes wrong:** High/low shows forecast period values, not today's actual range
**Why it happens:** `next_6_hours.air_temperature_max/min` covers a 6h window, not the full day
**How to avoid:** Scan all timeseries entries for today (midnight to midnight) and take the global max/min of `instant.details.air_temperature`, OR aggregate `next_6_hours` max/min across today's periods
**Warning signs:** High/low changes throughout the day in unexpected ways

### Pitfall 4: Animation Performance on Pixoo
**What goes wrong:** Frame rate drops, device lockup, laggy display
**Why it happens:** Generating complex animations + pushing frames too fast
**How to avoid:** Keep animations simple (few particles, no alpha blending); limit animation frame rate to ~2-4 FPS; only animate weather zone, composite with static zones
**Warning signs:** push_frame taking >200ms, device becoming unresponsive

### Pitfall 5: Symbol Code Variants
**What goes wrong:** KeyError when looking up icon for unknown symbol_code
**Why it happens:** ~50 symbol codes with `_day`/`_night`/`_polartwilight` suffixes; easy to miss edge cases
**How to avoid:** Strip suffix to get base code; map base code to icon group; apply day/night variant separately. Always have a fallback icon.
**Warning signs:** Crashes during nighttime or polar twilight periods

## Code Examples

### Fetching Weather from MET Locationforecast 2.0
```python
# Source: https://api.met.no/weatherapi/locationforecast/2.0/documentation
import requests

API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "divoom-hub/0.1 github.com/jdl/divoom-hub"

def fetch_forecast(lat: float, lon: float, last_modified: str | None = None) -> dict | None:
    headers = {"User-Agent": USER_AGENT}
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    resp = requests.get(
        API_URL,
        params={"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"},
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 304:
        return None  # Data unchanged, use cache
    resp.raise_for_status()
    return resp.json()
```

### Parsing Current Conditions from Timeseries
```python
# Source: https://docs.api.met.no/doc/ForecastJSON.html
def parse_current(timeseries: list[dict]) -> dict:
    """Extract current conditions from first timeseries entry."""
    entry = timeseries[0]
    instant = entry["data"]["instant"]["details"]
    next_1h = entry["data"].get("next_1_hours", {})

    return {
        "temperature": instant["air_temperature"],  # Celsius float
        "symbol_code": next_1h.get("summary", {}).get("symbol_code", "cloudy"),
        "precipitation_mm": next_1h.get("details", {}).get("precipitation_amount", 0.0),
        "precipitation_prob": next_1h.get("details", {}).get("probability_of_precipitation", 0.0),
    }
```

### Extracting Today's High/Low
```python
from datetime import date

def parse_high_low(timeseries: list[dict]) -> tuple[float, float]:
    """Scan today's timeseries entries for temperature extremes."""
    today = date.today().isoformat()
    temps = []
    for entry in timeseries:
        if entry["time"].startswith(today):
            temps.append(entry["data"]["instant"]["details"]["air_temperature"])
    if not temps:
        # Fallback: use next_6_hours from first entry
        first = timeseries[0]["data"]
        n6h = first.get("next_6_hours", {}).get("details", {})
        return (n6h.get("air_temperature_max", 0), n6h.get("air_temperature_min", 0))
    return (max(temps), min(temps))
```

### Symbol Code Grouping
```python
# Source: https://github.com/metno/weathericons + https://nrkno.github.io/yr-weather-symbols/
# MET symbol_codes: "clearsky_day", "partlycloudy_night", "rain", "heavysnow", etc.
# Strip _day/_night/_polartwilight suffix to get base code, then group.

ICON_GROUP = {
    # Group -> base symbol codes
    "clear":     {"clearsky", "fair"},
    "partcloud": {"partlycloudy"},
    "cloudy":    {"cloudy"},
    "rain":      {"rain", "lightrain", "heavyrain", "rainshowers", "lightrainshowers", "heavyrainshowers"},
    "sleet":     {"sleet", "lightsleet", "heavysleet", "sleetshowers", "lightsleetshowers", "heavysleetshowers"},
    "snow":      {"snow", "lightsnow", "heavysnow", "snowshowers", "lightsnowshowers", "heavysnowshowers"},
    "thunder":   {"rainshowersandthunder", "heavyrainshowersandthunder", "lightrainshowersandthunder",
                  "rainandthunder", "heavyrainandthunder", "lightrainandthunder",
                  "sleetshowersandthunder", "heavysleetshowersandthunder", "lightsleetshowersandthunder",
                  "sleetandthunder", "heavysleetandthunder", "lightsleetandthunder",
                  "snowshowersandthunder", "heavysnowshowersandthunder", "lightsnowshowersandthunder",
                  "snowandthunder", "heavysnowandthunder", "lightsnowandthunder"},
    "fog":       {"fog"},
}

def symbol_to_group(symbol_code: str) -> str:
    """Map MET symbol_code to icon group. Returns 'cloudy' as fallback."""
    base = symbol_code.replace("_day", "").replace("_night", "").replace("_polartwilight", "")
    for group, codes in ICON_GROUP.items():
        if base in codes:
            return group
    return "cloudy"  # safe fallback

def is_day(symbol_code: str) -> bool:
    """Determine if it's daytime from symbol_code suffix."""
    return "_night" not in symbol_code and "_polartwilight" not in symbol_code
```

### Simple Pixel Art Icon (PIL drawing)
```python
from PIL import Image, ImageDraw

def draw_sun_icon(size: int = 10) -> Image.Image:
    """Draw a simple sun icon as RGBA."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Yellow circle center
    cx, cy = size // 2, size // 2
    r = size // 3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 200, 50, 255))
    # Rays as 1px lines
    for angle_offset in range(0, 360, 45):
        # simplified -- actual implementation uses trig
        pass
    return img
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Yr API v1 (XML) | Locationforecast 2.0 (JSON) | 2020 | JSON only; XML deprecated |
| Locationforecast 1.6 | Locationforecast 2.0 | Ongoing (1.6 termination: 2026-03-16) | Must use 2.0; 1.6 dies next month |
| weathericon 1.1 (numbered codes) | Symbol code strings | 2020 | Use string codes like "clearsky_day", not old numeric IDs |

**Deprecated/outdated:**
- Locationforecast 1.6: Being terminated 2026-03-16. Must use 2.0.
- XML format: Deprecated in favor of JSON.
- Numeric weather icon codes: Replaced by string symbol_codes.

## Open Questions

1. **Exact animation frame rate**
   - What we know: Pixoo 64 handles ~10 FPS for full-frame pushes; current loop sleeps 1s
   - What's unclear: Whether 2-4 FPS weather animation will cause visible stutter alongside bus/clock updates
   - Recommendation: Start with 2 FPS (500ms sleep when animating), measure, adjust. Only re-render weather zone overlay, composite with cached static zones.

2. **Ladeveien altitude for API call**
   - What we know: Trondheim center is ~63.43 N, 10.40 E. MET API accepts optional altitude.
   - What's unclear: Whether altitude matters for a city-level forecast
   - Recommendation: Omit altitude parameter; MET defaults to model terrain height which is fine for Trondheim.

## Sources

### Primary (HIGH confidence)
- MET Weather API main page: https://api.met.no/
- Locationforecast 2.0 documentation: https://api.met.no/weatherapi/locationforecast/2.0/documentation
- Locationforecast data model: https://docs.api.met.no/doc/locationforecast/datamodel.html
- Forecast JSON format: https://docs.api.met.no/doc/ForecastJSON.html
- MET Weather API Terms of Service: https://api.met.no/doc/TermsOfService
- MET Weather Icons repo: https://github.com/metno/weathericons
- Yr weather symbols reference: https://nrkno.github.io/yr-weather-symbols/

### Secondary (MEDIUM confidence)
- metno-locationforecast PyPI: https://pypi.org/project/metno-locationforecast/ (confirms API usage patterns)
- MET developer getting started: https://developer.yr.no/doc/GettingStarted/

### Tertiary (LOW confidence)
- None -- all findings verified against official MET documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using existing project dependencies (requests, Pillow), no new packages
- Architecture: HIGH -- follows established bus provider pattern, well-understood PIL rendering
- Pitfalls: HIGH -- MET API is well-documented with clear terms of service; animation risks are standard embedded display concerns
- API data model: HIGH -- verified against official MET documentation

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable API, 30-day validity)
