# Phase 10: Radial Ray System - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current downward-falling random sun rays with radial beams that emit outward from the corner-anchored sun body at (63, 0). Rays spread in a downward-facing fan, fade with distance, cycle continuously, and render across two depth layers (9 far behind text, 5 near in front). The sun body itself (Phase 9) is untouched.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all visual tuning decisions to Claude, with feedback to come during UAT. The following areas are all open for Claude to decide:

**Fan spread & angle:**
- Exact angular range of the downward-facing fan from corner position
- Ray distribution across the fan (even vs jittered)
- Zone coverage (how far rays reach across the 64x24 weather zone)

**Ray visual style:**
- Ray thickness (1px vs 2px, uniform vs mixed by layer)
- Whether rays taper along their length
- Edge treatment (hard pixel lines vs soft glow halo)
- Length variation between individual rays

**Ray motion & speed:**
- Motion curve (constant, accelerating, or decelerating)
- Whether rays have angular drift as they travel outward
- Speed differentiation between near and far layers (parallax)
- Overall animation pacing (calm ambient vs active radiating)

**Fade & color tuning:**
- Whether color shifts along ray length or stays uniform warm yellow
- Fade curve shape (linear vs exponential vs custom)
- Alpha ranges for LED visibility on both layers
- How quickly rays cycle (linger time before respawn)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User will provide feedback during UAT (verify-work) after implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-radial-ray-system*
*Context gathered: 2026-02-23*
