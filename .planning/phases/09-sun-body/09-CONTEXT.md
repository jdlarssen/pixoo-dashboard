# Phase 9: Sun Body - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Visible half-sun semicircle with two-layer glow anchored at the top-right corner of the weather zone. Replaces the current small full circle (r=3 at 48,4) with a larger corner-anchored sun. Rays and ray animation belong to Phase 10.

</domain>

<decisions>
## Implementation Decisions

### Sun positioning & shape
- Corner-anchored: sun center placed at the top-right corner of the weather zone, clipped by BOTH the top edge and right edge
- This creates a quarter-sun / corner sunrise arc rather than a half-circle peeking over just the top
- The original requirement spec of (48, 0) needs adjustment — push center further right (e.g., toward 58-63, 0 or even beyond zone bounds) so both edges clip
- The visible arc should still be recognizable as a sun

### Claude's Discretion
- **Radius**: r=7 specified in requirements but may need adjustment for corner placement — pick what gives the best visible arc
- **Smoothness**: Anti-aliased vs pixel-art edges — decide based on what other display elements use
- **Color palette**: Warm yellow family — choose specific hue, saturation, and color shift between inner/outer layers based on LED panel visibility
- **Inner brightness**: Alpha for inner body (current is 200) — balance visibility vs LED bloom
- **Outer glow spread**: How many pixels beyond the body (+1-4px) — pick what's visible without overwhelming the zone
- **Glow transition**: Hard step (two concentric shapes) vs smooth gradient — decide based on what's achievable and visible at pixel scale
- **Outer glow alpha**: Must be above LED visibility threshold (~15) — pick intensity that creates warmth without distraction
- **Clipping approach**: Draw full circle and let zone clip, or pre-clip — pick what's cleanest to implement and test
- **Animation**: Static body or subtle pulse — decide based on value vs noise at this scale
- **Text interaction**: Sun body layer placement (bg only, or split bg/fg), dimming under text overlap, ambient light effects — decide based on actual text positions in the weather zone layout and readability
- **Text position check**: Verify where weather text (temp, hi/lo, description) renders relative to the top-right corner before deciding overlap strategy

</decisions>

<specifics>
## Specific Ideas

- User specifically chose corner-anchored over top-edge-only — they want the sun tucked into the corner, not just sitting above the zone
- The corner placement implies the visible sun arc is smaller than a full semicircle — more like a sunrise peeking from the corner
- When checking text overlap, the user wasn't sure about exact text positions — researcher should verify the weather zone layout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-sun-body*
*Context gathered: 2026-02-23*
