# Roadmap: Divoom Hub v1.1

## Overview

v1.1 is a focused polish milestone: fix the weather animation color issue that makes rain text indistinguishable from rain particles, then document the complete (fixed) project with a comprehensive Norwegian README. Color fix first so the README describes the correct state.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-6 (shipped 2026-02-21)
- 🚧 **v1.1 Documentation & Polish** - Phases 7-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-6) - SHIPPED 2026-02-21</summary>

Archived to `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v1.1 Documentation & Polish

- [ ] **Phase 7: Weather Color Fix** - Make rain/snow text and animation particles visually distinct on the physical LED display
- [ ] **Phase 8: Norwegian README** - Comprehensive Norwegian-language README documenting the entire project

## Phase Details

### Phase 7: Weather Color Fix
**Goal**: Weather text and animation particles are visually distinct on the physical Pixoo 64 display across all weather conditions
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: FARGE-01, FARGE-02, FARGE-03
**Success Criteria** (what must be TRUE):
  1. Rain indicator text ("Regn") is clearly readable against rain animation particles on the physical Pixoo 64 at 2+ meters
  2. All 8 weather animation types (rain, snow, sun, fog, thunder, cloudy, partly cloudy, clear night) show readable text with no color collision against their animation layer
  3. Automated tests assert color-identity properties (rain particles are blue-dominant, snow particles are white-ish, text color contrasts with all particle colors) to prevent future regression
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md -- Color palette tuning (text colors + particle RGB values for all 8 animation types)
- [ ] 07-02-PLAN.md -- Color-identity regression tests (channel-dominance + contrast assertions)

### Phase 8: Norwegian README
**Goal**: A reader can understand, install, configure, run, and maintain Divoom Hub from the README alone -- entirely in Norwegian
**Depends on**: Phase 7 (color fix must be complete so README documents correct animation behavior)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09, DOC-10, DOC-11, DOC-12, DOC-13, DOC-14, DOC-15
**Success Criteria** (what must be TRUE):
  1. A developer finding the repo can read the Norwegian project overview, see the display photo placeholder, and understand what Divoom Hub does within 30 seconds
  2. A developer can clone the repo and get the dashboard running on their Pixoo 64 by following the prerequisites, installation, configuration (.env), and usage sections step-by-step
  3. The README includes the "Bygget med Claude Code" badge near the top and an AI development transparency section explaining how Claude Code was used to build the project
  4. Technical sections (architecture, APIs, weather animations, Discord, Norwegian characters, error resilience, birthday easter egg) provide enough depth for someone to understand the system and contribute or fork
  5. No personal data (real GPS coordinates, real Discord tokens, real bus stop IDs from .env) appears in the README -- only safe placeholder values
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md -- Core README (overview, badge, zone diagram, install, config, usage, launchd, AI transparency)
- [ ] 08-02-PLAN.md -- Technical deep-dive (architecture, APIs, Discord, weather animations, fonts, error resilience, birthday)

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 7. Weather Color Fix | v1.1 | 0/2 | Not started | - |
| 8. Norwegian README | v1.1 | 0/? | Not started | - |
