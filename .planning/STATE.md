# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing -- without pulling out your phone.
**Current focus:** Phase 11: Discord Status Logging for Remote Monitoring

## Current Position

Phase: 11 (Discord Status Logging for Remote Monitoring)
Plan: 2 of 2 complete in current phase
Status: Phase 11 complete -- all monitoring plans finished
Last activity: 2026-02-24 -- Completed 11-02 bot extension and main loop integration

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 4 (since v1.2)
- Average duration: 5min
- Total execution time: 19min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 09 | 1 | 1min | 1min |
| 10 | 1 | 3min | 3min |
| 11 | 2 | 15min | 8min |

## Milestone History

| Milestone | Phases | Plans | Shipped |
|-----------|--------|-------|---------|
| v1.0 MVP | 1-6 | 15 | 2026-02-21 |
| v1.1 Documentation & Polish | 7-8 | 4 | 2026-02-21 |

## Accumulated Context

### Roadmap Evolution

- Phase 11 added: Discord status logging for remote monitoring

### Decisions

Full log in PROJECT.md Key Decisions table.

- **09-01:** Radius 8 for corner-anchored sun (visible arc ~64 body + ~65 glow pixels)
- **09-01:** Glow spread +2px at alpha 60; static body (no pulse at 1 FPS)
- **10-01:** 95-160 degree fan range for polar rays from top-right corner
- **10-01:** Draw sun body after far rays to prevent PIL overwrite of body pixels
- **10-01:** Re-randomize ray parameters on respawn for organic variety
- **11-01:** Debounce thresholds: bus_api 3 failures/900s repeat, weather_api 2/1800s, device 5/300s, default 3/600s
- **11-01:** MonitorBridge.send_embed() uses fut.result(timeout=5.0) for delivery confirmation
- **11-01:** HealthTracker works with monitor=None for testing and disabled monitoring
- **11-02:** on_ready_callback pattern defers MonitorBridge creation until bot event loop is available
- **11-02:** Monitor and display channels use independent if/if blocks for defensive separation
- **11-02:** Bus stop names resolved dynamically via EnTur API; weather location via reverse geocoding
- **11-02:** All health_tracker calls guarded with `if health_tracker:` for zero overhead when disabled

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 11-02-PLAN.md -- Phase 11 complete
Resume file: None
