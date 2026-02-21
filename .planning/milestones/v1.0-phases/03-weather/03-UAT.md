---
status: diagnosed
phase: 03-weather
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-20T20:00:00Z
updated: 2026-02-20T20:58:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Weather temperature in weather zone
expected: Run the dashboard. The weather zone displays the current temperature for Trondheim as a number. Positive temps in white, negative in blue. No minus sign, no degree symbol.
result: pass

### 2. Weather icon next to clock
expected: The clock zone shows a small weather icon (sun, cloud, rain, snow, etc.) composited to the right of the time digits, matching current conditions.
result: pass

### 3. High/low temperatures
expected: The weather zone shows today's high and low temperatures in dim gray below or near the current temperature.
result: pass

### 4. Weather animation
expected: The weather zone background shows a subtle animated effect matching current conditions (e.g., falling rain drops, drifting snow flakes, moving clouds, sun glow). Animation should not obscure the temperature text.
result: issue
reported: "I don't see it, it might be too subtle"
severity: minor

### 5. Rain indicator
expected: If precipitation is occurring, the weather zone shows a rain indicator with the precipitation amount in mm. If no precipitation, no rain indicator is shown.
result: pass

### 6. Weather data refreshes
expected: Weather data updates automatically. After 10+ minutes the display should still show current weather (not stale or blank). The main loop continues running without errors.
result: skipped
reason: Requires 10+ minute wait, impractical to test live

## Summary

total: 6
passed: 4
issues: 1
pending: 0
skipped: 1

## Gaps

- truth: "Weather zone background shows a subtle animated effect matching current conditions"
  status: failed
  reason: "User reported: I don't see it, it might be too subtle"
  severity: minor
  test: 4
  root_cause: "Double alpha application in renderer.py compositing -- alpha_composite() + paste(mask=alpha) squares effective opacity (20% becomes ~4%). Compounded by PixooClient 1s rate limiter dropping 75% of 4-FPS frames."
  artifacts:
    - path: "src/display/renderer.py"
      issue: "Lines 128-137: alpha_composite + paste(mask=alpha) applies transparency twice"
    - path: "src/device/pixoo_client.py"
      issue: "Lines 62-66: 1s rate limiter silently drops most animation frames"
    - path: "src/display/weather_anim.py"
      issue: "Alpha values 30-50 too low for LED hardware even without double-alpha bug"
    - path: "src/main.py"
      issue: "0.25s animation loop conflicts with 1s device rate limit"
  missing:
    - "Fix compositing to apply alpha only once (alpha_composite OR paste mask, not both)"
    - "Align animation frame rate with device rate limit"
    - "Increase alpha values and particle sizes for LED hardware visibility"
  debug_session: ".planning/debug/weather-animation-too-subtle.md"
