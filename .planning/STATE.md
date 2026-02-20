# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing -- without pulling out your phone.
**Current focus:** Phase 3: Weather (In Progress)

## Current Position

Phase: 3 of 4 (Weather)
Plan: 1 of 2 in current phase
Status: Executing Phase 3 -- Plan 01 complete
Last activity: 2026-02-20 -- Completed 03-01-PLAN.md

Progress: [██████░░░░] 62%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 9 min
- Total execution time: 0.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | 24 min | 12 min |
| 02-bus-departures | 2 | 15 min | 7.5 min |
| 03-weather | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 01-02 (20 min), 02-01 (3 min), 02-02 (12 min), 03-01 (3 min)
- Trend: Consistent

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: RLBL-01 (connection refresh) placed in Phase 1, not Phase 4, because research shows 300-push lockup hits after ~5 hours and must be prevented from day one
- [Roadmap]: 4 phases derived from natural delivery boundaries despite comprehensive depth setting; requirements cluster cleanly into foundation/bus/weather/polish without artificial splits
- [01-01]: draw_image() accepts PIL Image objects directly -- no temp file needed for device push
- [01-01]: SimulatorConfiguration imported from pixoo.configurations.simulatorconfiguration (not top-level pixoo import)
- [01-01]: Converted font files (.pil/.pbm) gitignored -- regenerated from BDF at runtime
- [01-02]: Norwegian day/month names use manual dictionaries instead of locale -- avoids system locale dependency
- [01-02]: DisplayState equality drives dirty flag -- only re-renders when minute changes
- [01-02]: Zone pixel budget: clock 14px, date 9px, divider 1px, bus 19px, divider 1px, weather 20px = 64px
- [02-01]: Quay IDs from Entur: NSR:Quay:73154 (Sentrum) and NSR:Quay:73152 (Lade/Strindheim)
- [02-01]: DisplayState bus fields use tuples (not lists) to preserve hashability for dirty flag
- [02-01]: fetch_departures_safe returns list[int] | None -- simplified for renderer consumption
- [02-02]: Arrow directions match actual travel: <S (Sentrum leftward), >L (Lade rightward)
- [02-02]: 3 departures per direction (user feedback) -- more useful for planning
- [02-02]: Cancelled departures filtered silently -- request extra from API, skip cancelled entries
- [02-02]: Bus zone uses 5x8 font for countdown numbers; zone-renderer-helper pattern established
- [03-01]: Direct requests.get to MET API -- no wrapper library needed for single GET endpoint
- [03-01]: If-Modified-Since caching via module-level globals for MET API compliance
- [03-01]: High/low temps: scan today's timeseries entries, fallback to next_6_hours
- [03-01]: DisplayState weather fields use TYPE_CHECKING import to avoid circular imports

### Pending Todos

None yet.

### Blockers/Concerns

- ~~Phase 1 needs hands-on Norwegian bitmap font testing~~ RESOLVED: hzeller BDF fonts confirmed rendering ae/oe/aa in all 3 sizes (4x6, 5x8, 7x13)
- ~~Phase 2 requires Ladeveien quay ID lookup (5-minute mechanical task via stoppested.entur.org) before implementation~~ RESOLVED: Quay IDs discovered via Entur API -- NSR:Quay:73154 (Sentrum) and NSR:Quay:73152 (Lade/Strindheim)

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 03-01-PLAN.md (weather data provider -- Plan 02 remaining)
Resume file: None
