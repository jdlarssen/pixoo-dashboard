# Requirements: Divoom Hub

**Defined:** 2026-02-21
**Core Value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing -- without pulling out your phone.

## v1.1 Requirements

Requirements for Documentation & Polish milestone. Each maps to roadmap phases.

### Dokumentasjon (README)

- [ ] **DOC-01**: README has project overview in Norwegian with display photo placeholder
- [ ] **DOC-02**: README has 64x64 zone layout diagram (ASCII art)
- [ ] **DOC-03**: README has prerequisites section (Python 3.10+, Pixoo 64, LAN)
- [ ] **DOC-04**: README has installation guide (clone, venv, pip install)
- [ ] **DOC-05**: README has configuration guide (.env variables with required/optional flags)
- [ ] **DOC-06**: README has usage section (running, --simulated, --save-frame)
- [ ] **DOC-07**: README has launchd service setup (step-by-step)
- [ ] **DOC-08**: README has "Bygget med Claude Code" badge and AI development transparency section
- [ ] **DOC-09**: README has architecture overview (module map, data flow)
- [ ] **DOC-10**: README has API documentation (Entur, MET Norway gotchas)
- [ ] **DOC-11**: README has Discord message override section
- [ ] **DOC-12**: README has weather animation documentation (3D depth system)
- [ ] **DOC-13**: README documents Norwegian character support (BDF fonts, aeoeaa)
- [ ] **DOC-14**: README documents error resilience (staleness dot, fallback, 300-push refresh)
- [ ] **DOC-15**: README mentions birthday easter egg

### Fargefiks (Weather Colors)

- [ ] **FARGE-01**: Rain indicator text is visually distinct from rain animation particles on LED display
- [ ] **FARGE-02**: All 8 weather animation types verified for text/animation contrast
- [ ] **FARGE-03**: Color-identity regression tests prevent future color clashes

## Future Requirements

None -- v1.1 is a focused polish milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| English README | Norwegian explicitly chosen for target audience; browser translation available |
| Nynorsk variant | User writes Bokmal; dual-language doubles maintenance |
| Auto-generated API docs (Sphinx/mkdocs) | Disproportionate to 2,321 LOC codebase |
| Configurable color picker | Over-engineering; 1-2 constant changes suffice |
| Per-weather-condition text colors | Adds complexity for minimal gain; use colors that contrast with all animations |
| Norwegian code comments | Convention is English for code; Norwegian for user-facing docs only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOC-01 | Phase 8 | Pending |
| DOC-02 | Phase 8 | Pending |
| DOC-03 | Phase 8 | Pending |
| DOC-04 | Phase 8 | Pending |
| DOC-05 | Phase 8 | Pending |
| DOC-06 | Phase 8 | Pending |
| DOC-07 | Phase 8 | Pending |
| DOC-08 | Phase 8 | Pending |
| DOC-09 | Phase 8 | Pending |
| DOC-10 | Phase 8 | Pending |
| DOC-11 | Phase 8 | Pending |
| DOC-12 | Phase 8 | Pending |
| DOC-13 | Phase 8 | Pending |
| DOC-14 | Phase 8 | Pending |
| DOC-15 | Phase 8 | Pending |
| FARGE-01 | Phase 7 | Pending |
| FARGE-02 | Phase 7 | Pending |
| FARGE-03 | Phase 7 | Pending |

**Coverage:**
- v1.1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation*
