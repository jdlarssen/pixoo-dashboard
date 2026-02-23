# Requirements: Divoom Hub

**Defined:** 2026-02-23
**Core Value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing — without pulling out your phone.

## v1.2 Requirements

Requirements for sun ray overhaul. Each maps to roadmap phases.

### Animation

- [ ] **ANIM-01**: Sun appears as a half-sun semicircle (r=7) clipped at the top-right of the weather zone at (48, 0)
- [ ] **ANIM-02**: Sun body has two-layer glow (outer dim, inner bright warm yellow)
- [ ] **ANIM-03**: Rays emit radially outward from sun center across a downward-facing fan
- [ ] **ANIM-04**: Ray alpha fades with distance from sun
- [ ] **ANIM-05**: Rays respawn at sun origin when faded or exited zone
- [ ] **ANIM-06**: Far rays (9) on bg layer, near rays (5) on fg layer — depth system preserved
- [ ] **ANIM-07**: Staggered initial ray distances so animation starts mid-flow

### Testing

- [ ] **TEST-01**: Sun body tests updated for new position and radius
- [ ] **TEST-02**: Ray origin clustering test — rays concentrate near sun, not randomly scattered

## Future Requirements

None — this is a focused overhaul milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dynamic ray count by weather intensity | No intensity parameter exists for clear sky |
| Sunrise/sunset color transitions | Belongs in a new animation class |
| Sun position varying with time of day | Zone too small for meaningful motion |
| Wind effect on sun rays | Polar rays can't meaningfully receive cartesian wind offsets |
| Curved or width-varying rays | No visible benefit at 64x64 resolution |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANIM-01 | — | Pending |
| ANIM-02 | — | Pending |
| ANIM-03 | — | Pending |
| ANIM-04 | — | Pending |
| ANIM-05 | — | Pending |
| ANIM-06 | — | Pending |
| ANIM-07 | — | Pending |
| TEST-01 | — | Pending |
| TEST-02 | — | Pending |

**Coverage:**
- v1.2 requirements: 9 total
- Mapped to phases: 0
- Unmapped: 9

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 after initial definition*
