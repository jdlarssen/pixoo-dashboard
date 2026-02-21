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

