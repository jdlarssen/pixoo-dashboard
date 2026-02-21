---
status: resolved
trigger: "Sunrays showing at night in weather zone; weather icon looks like rotated comma"
created: 2026-02-21T17:00:00+01:00
updated: 2026-02-21T17:05:00+01:00
---

## Current Focus

hypothesis: CONFIRMED and FIXED
test: 112 tests pass (8 new night animation tests)
expecting: N/A -- verified
next_action: Archive and commit

## Symptoms

expected: At nighttime, the weather animation should NOT show sunrays. It should show an appropriate nighttime animation (e.g. stars, moon, or just no sun-related animation). The weather icon should also reflect nighttime conditions.
actual: The display shows sunray animations in the weather zone despite it being dark outside. The weather icon in the clock zone looks like a rotated comma.
errors: No error messages -- visual/logic issue only.
reproduction: Run the dashboard at night (after sunset) in Trondheim, Norway. Current time ~17:00, Feb 21. Sunset ~16:30-17:00.
started: First observation -- dashboard just set up today.

## Eliminated

(None -- first hypothesis was correct)

## Evidence

- timestamp: 2026-02-21T17:00:30
  checked: weather_anim.py _ANIMATION_MAP and get_animation()
  found: _ANIMATION_MAP maps "clear" -> SunAnimation, "partcloud" -> SunAnimation. get_animation() receives only the group name (no day/night flag). No night-specific animation class exists.
  implication: At night, "clearsky_night" -> symbol_to_group strips "_night" -> group "clear" -> SunAnimation. Sunrays always play regardless of time.

- timestamp: 2026-02-21T17:00:45
  checked: main.py lines 177-181 (animation swap logic)
  found: new_group = symbol_to_group(weather_data.symbol_code) passes group to get_animation(). The is_day flag from WeatherData/DisplayState is never consulted for animation selection. Also, animation only swaps when group changes -- a day->night transition for the same group (e.g. "clear") would never trigger an animation swap.
  implication: Animation system is completely day/night unaware at both selection and transition levels.

- timestamp: 2026-02-21T17:01:00
  checked: weather_icons.py _draw_moon() -- ASCII rendered the 10x10 icon
  found: The crescent moon renders as an asymmetric thin blob. With r=3, the cut ellipse at (cx-r+2, cy-r-1) to (cx+r+2, cy+r-1) produces a sliver that looks like "a comma rotated 90 degrees to the right." The icon code IS day/night aware (correct logic), but the pixel art is poor at 10px.
  implication: Icon selection is correct (moon at night), but the moon shape needs improvement.

## Resolution

root_cause: TWO ISSUES:
1. PRIMARY -- Animation selection ignores day/night. _ANIMATION_MAP maps "clear" and "partcloud" to SunAnimation unconditionally. get_animation() only takes weather_group, not a day/night flag. main.py only swaps animation when group changes, not when day/night changes. Result: sunrays at night.
2. SECONDARY -- Moon icon pixel art at 10px is unrecognizable. The r=3 circle with cut offset (2, -1) creates a thin sliver that looks like a rotated comma, not a crescent moon.

fix:
1. Added ClearNightAnimation class (twinkling stars with two depth layers) to weather_anim.py
2. Added _NIGHT_ANIMATION_MAP with night overrides for "clear" and "partcloud"
3. Updated get_animation() to accept is_night keyword argument
4. Updated main.py to pass is_night flag and track last_weather_night state
5. Animation now swaps when EITHER weather group OR day/night changes
6. Improved _draw_moon() pixel art: larger r=4 circle, better-centered crescent cut

verification: 112 tests pass (104 original + 8 new). New tests cover: night animation type selection, day/night backward compatibility, layer format, visibility, color identity. ASCII-rendered improved moon icon confirms recognizable crescent shape.

files_changed:
- src/display/weather_anim.py
- src/display/weather_icons.py
- src/main.py
- tests/test_weather_anim.py
