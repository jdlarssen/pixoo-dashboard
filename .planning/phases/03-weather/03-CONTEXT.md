# Phase 3: Weather - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Fill the weather zone with live Yr/MET data: current temperature, weather condition icon, today's high/low, and a rain indicator. Also place a weather condition icon next to the clock in the clock zone. The weather zone gets animated backgrounds based on current conditions.

</domain>

<decisions>
## Implementation Decisions

### Weather icon placement
- Weather condition icon goes to the RIGHT of the clock digits in the clock zone (not in the weather zone)
- Icons should have day/night variants (sun during day, moon at night, etc.)
- The weather zone below becomes text-only for temperature data and rain info

### Animated weather backgrounds
- The weather zone (64x20) gets animated background effects based on current conditions
- Raindrops falling when raining, sun rays when sunny, cloud drift when foggy/overcast, etc.
- Animation drives more frequent frame updates for the weather zone
- Text (temperature, high/low) renders on top of the animation

### Temperature display
- No degree symbol or "C" — just the number (e.g., "12" not "12°")
- Negative temperatures: use blue text color instead of a minus sign — saves pixel space
- Positive temperatures: standard color (white or warm tone — Claude's discretion)

### High/low temperatures
- Today's high and low displayed in the weather zone
- Exact positioning (same line as current temp vs separate line) is Claude's discretion based on pixel budget

### Rain indicator
- Communicated primarily through the animated background (visible rain effect)
- Additional text/visual indicator details at Claude's discretion based on what Yr data supports

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

</decisions>

<specifics>
## Specific Ideas

- "It would be amazing if the background is animated with rain drops if it's rain, and sun rays if it's sunny, clouds if it's foggy etc." — animated weather backgrounds in the weather zone
- Weather icon next to the clock, not in the weather zone — the clock zone has ~20px of free space to the right of the time digits
- Blue text for negative temperatures instead of minus sign — color communicates below zero
- Just the number for temperature, no degree symbol — minimalist, everyone knows it's Celsius in Norway

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-weather*
*Context gathered: 2026-02-20*
