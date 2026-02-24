# Milestones

## v1.0 Divoom Hub MVP (Shipped: 2026-02-21)

**Phases:** 6 | **Plans:** 15 | **Commits:** 77 | **LOC:** 3,767 Python (2,321 src + 1,446 tests)
**Timeline:** 2 days (2026-02-20 → 2026-02-21) | **Git range:** 7e95e7c..7a808a4
**Tests:** 96/96 passing | **Lint:** 0 errors

**Delivered:** Always-on entryway dashboard on Pixoo 64 displaying time, bus departures, and weather at a glance — 19/19 requirements satisfied.

**Key accomplishments:**
1. PIL/Pillow render pipeline with BDF bitmap fonts for Norwegian characters (æøå) on Pixoo 64
2. Entur GraphQL client for real-time bus departures from Ladeveien with countdown format and cancellation filtering
3. MET Norway weather API with pixel art icons and animated backgrounds (rain, snow, sun, fog, thunder) with 3D depth layering
4. Urgency color coding, auto-brightness scheduling, Discord message override, launchd service wrapper, birthday easter egg
5. Full verification coverage for all 19 requirements with 96 tests and staleness dot regression suite
6. Zero tech debt: dead code removed, Pillow deprecation fixed, SUMMARY frontmatter corrected

**Known Tech Debt (accepted):**
- 3 human verification items requiring physical device testing (animation visibility, weather refresh observation, launchd restart)

**Archives:** `milestones/v1.0-ROADMAP.md` | `milestones/v1.0-REQUIREMENTS.md` | `milestones/v1.0-MILESTONE-AUDIT.md`

---


## v1.1 Documentation & Polish (Shipped: 2026-02-21)

**Phases:** 2 | **Plans:** 4 | **Tasks:** 8 | **LOC:** 3,974 Python (src + tests)
**Timeline:** 2 days (2026-02-20 -> 2026-02-21) | **Git range:** a68bcef..d076829
**Requirements:** 18/18 complete (FARGE-01-03 + DOC-01-15)

**Delivered:** Weather color fix for LED display readability + comprehensive 414-line Norwegian README documenting the entire project from installation to architecture.

**Key accomplishments:**
1. Vivid weather color palette tuned for physical LED display -- rain particles distinctly blue, snow white, all 8 animation types readable at 2+ meters
2. Color-identity regression tests preventing future color clashes (channel-dominance + contrast assertions)
3. Comprehensive 414-line Norwegian README covering all 15 documentation requirements (overview, install, config, usage, launchd, AI transparency, architecture, APIs, Discord, animations, fonts, error resilience, birthday)
4. shields.io "Bygget med Claude Code" badge and AI development transparency section

**Known Tech Debt:** None.

**Archives:** `milestones/v1.1-ROADMAP.md` | `milestones/v1.1-REQUIREMENTS.md`

---


## v1.2 Sun Ray Overhaul (Shipped: 2026-02-24)

**Phases:** 3 | **Plans:** 4 | **Tasks:** 9 | **LOC:** 6,716 Python (3,676 src + 3,040 tests)
**Timeline:** 2 days (2026-02-23 → 2026-02-24) | **Git range:** cbe411d..6a66ca9
**Requirements:** 16/16 complete (ANIM-01-07 + TEST-01-03 + MON-01-06)

**Delivered:** Radial sun ray overhaul with corner-anchored half-sun body + Discord-based remote health monitoring with debounced error/recovery embeds.

**Key accomplishments:**
1. Corner-anchored quarter-sun body (r=8) with two-layer warm-yellow glow using PIL auto-clipping
2. Polar radial ray system in 95-160° fan with distance-based alpha fade and continuous respawn
3. MonitorBridge for thread-safe sync-to-async Discord embed delivery with 5s timeout
4. HealthTracker debounced state machine with per-component failure thresholds (bus=3, weather=2, device=5)
5. Discord bot extended with monitoring channel, status command, and startup/shutdown lifecycle embeds
6. Dynamic bus stop name and weather location resolution for human-readable startup embed

**Known Tech Debt:**
- `health_tracker._monitor` assigned via direct private attribute write (fragile if refactored to double-underscore)
- `HealthTracker(monitor=None)` tracks state in memory even when monitoring disabled (trivial overhead)

**Archives:** `milestones/v1.2-ROADMAP.md` | `milestones/v1.2-REQUIREMENTS.md` | `milestones/v1.2-MILESTONE-AUDIT.md`

---

