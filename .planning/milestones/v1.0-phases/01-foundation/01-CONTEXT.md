# Phase 1: Foundation - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Device communication with the Pixoo 64, PIL/Pillow render engine, 64x64 pixel layout establishing all information zones (clock, bus, weather), and live clock/date display in Norwegian. The display must run continuously for 8+ hours without device lockup.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User trusts Claude's judgment on all implementation decisions for this phase. Iteration will happen through UAT (user acceptance testing) after the phase is built.

The following areas are all at Claude's discretion:

**Screen layout**
- How to divide the 64x64 pixel grid between clock, bus zone, and weather zone
- Proportions, positions, and visual dividers between zones
- Best layout for readability from 2+ meters

**Clock appearance**
- Time digit size, pixel font style, 24-hour format
- Colon style (static vs blinking is v2 — keep static for now)
- Ensuring legibility from 2+ meters distance

**Date formatting**
- Norwegian date abbreviation style (e.g. "tor 20. feb")
- Positioning relative to the clock
- Pixel font with working ae/oe/aa characters

**Empty zone treatment**
- How bus and weather zones appear before data is wired up in Phases 2-3
- Whether to show labels, leave blank, or use placeholder content

**Device communication**
- Connection refresh strategy to prevent the 300-push lockup
- Frame push interval and refresh cycle

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants to iterate through UAT rather than pre-specifying visual details.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-20*
