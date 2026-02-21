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

