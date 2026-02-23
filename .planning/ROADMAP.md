# Roadmap: Divoom Hub

## Milestones

- ✅ **v1.0 MVP** - Phases 1-6 (shipped 2026-02-21)
- ✅ **v1.1 Documentation & Polish** - Phases 7-8 (shipped 2026-02-21)
- 🚧 **v1.2 Sun Ray Overhaul** - Phases 9-10 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-6) - SHIPPED 2026-02-21</summary>

Archived to `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v1.1 Documentation & Polish (Phases 7-8) - SHIPPED 2026-02-21</summary>

Archived to `.planning/milestones/v1.1-ROADMAP.md`

</details>

### 🚧 v1.2 Sun Ray Overhaul (In Progress)

**Milestone Goal:** Replace random sky-wide sun rays with radial beams emitting from a visible half-sun at the top-right of the weather zone.

**Phase Numbering:**
- Integer phases (9, 10): Planned milestone work
- Decimal phases (9.1, 9.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 9: Sun Body** - Half-sun semicircle with two-layer glow anchoring the weather zone
- [ ] **Phase 10: Radial Ray System** - Polar ray emission from sun with depth layers and fade

## Phase Details

### Phase 9: Sun Body
**Goal**: Users see a recognizable half-sun anchored at the top-right corner of the weather zone
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: ANIM-01, ANIM-02, TEST-01
**Success Criteria** (what must be TRUE):
  1. A visible semicircle appears clipped at the top-right of the weather zone, recognizable as a sun
  2. The sun body has a two-layer glow -- a dimmer outer ring and a brighter warm-yellow inner fill
  3. No sun pixels render above the weather zone boundary (clipping is clean)
  4. Sun body tests pass, asserting correct position, radius, and boundary clipping
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

### Phase 10: Radial Ray System
**Goal**: Sun rays emit outward from the sun body in a natural radial pattern with depth and fade
**Depends on**: Phase 9
**Requirements**: ANIM-03, ANIM-04, ANIM-05, ANIM-06, ANIM-07, TEST-02
**Success Criteria** (what must be TRUE):
  1. Rays visibly originate from the sun and spread outward in a downward-facing fan -- not random diagonal streaks
  2. Rays fade in brightness as they travel away from the sun, creating a light-emission effect
  3. Rays continuously respawn at the sun origin when they fade out or exit the zone -- animation never stalls
  4. Far rays appear behind weather text and near rays appear in front, preserving the depth effect
  5. Animation starts mid-flow with rays at staggered distances -- no initial burst from the sun
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 9. Sun Body | v1.2 | 0/? | Not started | - |
| 10. Radial Ray System | v1.2 | 0/? | Not started | - |
