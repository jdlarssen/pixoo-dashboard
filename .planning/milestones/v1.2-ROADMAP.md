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

- [x] **Phase 9: Sun Body** - Half-sun semicircle with two-layer glow anchoring the weather zone (completed 2026-02-23)
- [x] **Phase 10: Radial Ray System** - Polar ray emission from sun with depth layers and fade (completed 2026-02-23)

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
**Plans**: 1 plan

Plans:
- [ ] 09-01-PLAN.md — Corner-anchored quarter-sun body with two-layer glow and updated tests

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
**Plans**: 1 plan

Plans:
- [x] 10-01-PLAN.md — Polar radial ray system with distance fade, respawn, depth layers, and clustering test

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 9. Sun Body | v1.2 | Complete    | 2026-02-23 | - |
| 10. Radial Ray System | 1/1 | Complete   | 2026-02-23 | - |
| 11. Discord Status Logging | v1.2 | Complete    | 2026-02-24 | 2026-02-24 |

### Phase 11: Discord Status Logging for Remote Monitoring

**Goal**: Application health is remotely observable via Discord -- problems reported automatically, silence means healthy
**Depends on**: Phase 10
**Requirements**: MON-01, MON-02, MON-03, MON-04, MON-05, MON-06, TEST-03
**Success Criteria** (what must be TRUE):
  1. Startup embed appears in monitoring channel with config summary when app launches
  2. Error embeds appear after sustained component failures (debounced, not on first blip)
  3. Recovery embeds appear with downtime duration when failed components recover
  4. "status" command in monitoring channel returns a health snapshot embed
  5. App runs identically without DISCORD_MONITOR_CHANNEL_ID set -- zero overhead
  6. Existing display-message channel behavior is completely unchanged
**Plans**: 2 plans

Plans:
- [x] 11-01-PLAN.md -- Core monitoring module (MonitorBridge, HealthTracker, embed builders, tests)
- [x] 11-02-PLAN.md -- Bot extension, config, main loop integration, human verification
