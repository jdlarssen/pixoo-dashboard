# Requirements: Divoom Hub

**Defined:** 2026-02-23
**Core Value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing — without pulling out your phone.

## v1.2 Requirements

Requirements for sun ray overhaul. Each maps to roadmap phases.

### Animation

- [x] **ANIM-01**: Sun appears as a half-sun semicircle (r=7) clipped at the top-right of the weather zone at (48, 0)
- [x] **ANIM-02**: Sun body has two-layer glow (outer dim, inner bright warm yellow)
- [x] **ANIM-03**: Rays emit radially outward from sun center across a downward-facing fan
- [x] **ANIM-04**: Ray alpha fades with distance from sun
- [x] **ANIM-05**: Rays respawn at sun origin when faded or exited zone
- [x] **ANIM-06**: Far rays (9) on bg layer, near rays (5) on fg layer — depth system preserved
- [x] **ANIM-07**: Staggered initial ray distances so animation starts mid-flow

### Testing

- [x] **TEST-01**: Sun body tests updated for new position and radius
- [x] **TEST-02**: Ray origin clustering test — rays concentrate near sun, not randomly scattered

## Phase 11 Requirements

Requirements for Discord monitoring. Each maps to Phase 11 in roadmap.

### Monitoring

- [ ] **MON-01**: Startup and shutdown lifecycle embeds sent to dedicated monitoring Discord channel
- [x] **MON-02**: Error embeds with diagnostic context (component, error type, duration, last success) after debounced failure detection
- [x] **MON-03**: Recovery embeds with downtime duration when failed components recover
- [ ] **MON-04**: On-demand "status" command in monitoring channel returns health snapshot embed
- [ ] **MON-05**: Optional via DISCORD_MONITOR_CHANNEL_ID env var -- no channel configured = no monitoring, zero overhead
- [ ] **MON-06**: Existing display-message channel completely untouched

### Testing

- [x] **TEST-03**: HealthTracker debounce, recovery, and embed builder tests

## Future Requirements

None planned.

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
| ANIM-01 | Phase 9 | Complete |
| ANIM-02 | Phase 9 | Complete |
| ANIM-03 | Phase 10 | Complete |
| ANIM-04 | Phase 10 | Complete |
| ANIM-05 | Phase 10 | Complete |
| ANIM-06 | Phase 10 | Complete |
| ANIM-07 | Phase 10 | Complete |
| TEST-01 | Phase 9 | Complete |
| TEST-02 | Phase 10 | Complete |
| MON-01 | Phase 11 | Planned |
| MON-02 | Phase 11 | Planned |
| MON-03 | Phase 11 | Planned |
| MON-04 | Phase 11 | Planned |
| MON-05 | Phase 11 | Planned |
| MON-06 | Phase 11 | Planned |
| TEST-03 | Phase 11 | Planned |

**Coverage:**
- v1.2 requirements: 9 total, 9 complete
- Phase 11 requirements: 7 total, 0 complete
- Unmapped: 0

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-24 after Phase 11 planning*
