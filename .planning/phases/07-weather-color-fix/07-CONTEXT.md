# Phase 7: Weather Color Fix - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Make weather text and animation particles visually distinct on the physical Pixoo 64 display across all 8 weather conditions. Fix the rain text/particle color clash and tune all animations for better color saturation and clarity. Must be readable at 2+ meters in both bright and dim rooms.

</domain>

<decisions>
## Implementation Decisions

### Color change strategy
- Tune BOTH text colors and particle colors — not just one side
- The 3D depth layering (far/near particles with text sandwiched) stays as-is
- User will verify every weather condition on the physical Pixoo 64 display personally
- Foreground particles still render over text — preserve the depth effect

### Rain text behavior
- Precipitation text shows number only (e.g. "1.5mm"), no label like "Regn"
- Precipitation text should ONLY appear when there's actual precipitation (>0mm) — hide when dry
- This is a behavior change from current (always visible)

### Text readability
- Must be readable at 2+ meters in both well-lit and dim room conditions
- Brightness target: Claude's discretion (work across reasonable range)

### Animation tuning
- Review and tune ALL 8 weather animations, not just the broken rain one
- Current animations look "muddy" on the LED — colors need more saturation/contrast
- The 2-layer depth system (far dim + near bright) works well and should be preserved
- Particles should feel more vivid and distinct from each other across weather types

### Claude's Discretion
- Overall text color palette structure (unified vs current split of yellow temp / teal hi-lo / blue rain)
- Specific rain text color choice (whatever contrasts best with all animation types)
- Whether to add text outlines/shadows for readability or rely on color alone
- Rain text positioning (keep current or move if it improves readability)
- Realistic vs stylized particle colors (balance realism with LED readability)
- Target brightness level for optimization
- Specific RGB values and alpha tuning for all 8 animation types

</decisions>

<specifics>
## Specific Ideas

- Colors currently feel "muddy" on the physical LED — the main aesthetic complaint across all animations
- The 3D depth layering effect is appreciated and should not be diminished
- Rain is the worst offender: blue text on blue particles is the blocking issue

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-weather-color-fix*
*Context gathered: 2026-02-21*
