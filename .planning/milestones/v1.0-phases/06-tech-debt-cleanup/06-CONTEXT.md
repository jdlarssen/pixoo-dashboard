# Phase 6: Tech Debt Cleanup - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve all tech debt items identified in the v1.0 milestone audit: dead code, stale docstrings, Pillow deprecation fix, and SUMMARY frontmatter format gaps. This is a code-only cleanup phase — no new features, no behavior changes.

</domain>

<decisions>
## Implementation Decisions

### SUMMARY frontmatter format
- Claude's discretion on exact format (simple ID list vs ID+description), fitting existing frontmatter conventions
- Claude determines whether each requirement ID appears in one SUMMARY (primary plan) or allows duplicates across contributing plans
- Claude decides whether plans with no requirements get an empty list or omit the field
- Must be applied to all 13 existing SUMMARY.md files

### Pillow deprecation approach
- Claude determines whether to fix just the flagged `getdata()` call or audit all files for other Pillow deprecations
- Claude decides whether to document the Pillow 14 timeline or just fix the code
- Claude decides on verification level (run tests vs trust the swap)
- Claude checks whether pyproject.toml version requirements need updating

### Cleanup thoroughness
- **Scan config.py** for other unused constants beyond FONT_LARGE — clean sweep of that file
- **Check all main.py docstrings** for accuracy, not just the flagged `main_loop()` one
- Human verification items (animation visibility, weather refresh, launchd) are out of scope for this code-only phase — Claude decides if they need documenting
- Claude decides whether a re-audit is worthwhile after these small fixes

### Claude's Discretion
- SUMMARY frontmatter format details (structure, duplication policy, empty handling)
- Pillow deprecation audit scope and verification approach
- Whether human verification items get a documentation note
- Whether to re-run milestone audit after completion

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants config.py and main.py reviewed more broadly while touching them, but otherwise trusts Claude's judgment on all implementation details.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-tech-debt-cleanup*
*Context gathered: 2026-02-21*
