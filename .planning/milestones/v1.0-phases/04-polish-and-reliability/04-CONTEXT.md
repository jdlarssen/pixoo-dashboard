# Phase 4: Polish and Reliability - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Production-harden the dashboard for daily use: urgency coloring on bus departures, adaptive brightness, graceful error handling with staleness indicators, supervised auto-restart, Discord-based message override, and a full visual color pass across all zones. The dashboard should be both useful and fun to look at.

</domain>

<decisions>
## Implementation Decisions

### Urgency color thresholds
- Green text: > 10 minutes until departure
- Yellow text: 5-10 minutes until departure
- Red text: < 5 minutes until departure
- Dimmed/greyed out: < 2 minutes (bus has just left) — still shown, not replaced
- Color applied to departure countdown text only (not backgrounds)
- Direction labels (Sentrum, Lade): Claude's discretion on whether they inherit urgency color or stay neutral

### Brightness schedule
- Dim mode: 21:00 to 06:00 (household bedtime/wake schedule)
- Night brightness: 15-25% range (soft glow — readable without lighting up the room)
- Day brightness: full (100%)
- Transition style (gradual ramp vs hard switch): Claude's discretion
- Whether schedule lives in config or is hardcoded: Claude's discretion

### Error & staleness display
- When API fails: show last known data with a staleness indicator (approach is Claude's discretion)
- Staleness thresholds (how long before data is "too old"): Claude's discretion based on data type
- When data is too old to show: display dash placeholders ("--" or "- min") — not blank
- Clock error detection: Claude's discretion (system clock is generally trusted)

### Message override (Discord integration)
- Messages sent via Discord bot — user types in a Discord channel from phone, bot forwards to display
- Messages are persistent reminders (like "Remember a bag for shopping"), NOT flash notifications
- Messages stay on display until explicitly cleared or replaced by a new message
- Clearing: send a clear command in Discord, OR new message replaces old one
- Display placement: user prefers message alongside existing dashboard content (bottom-right, next to weather) rather than full-screen takeover — if space doesn't permit on 64x64, fall back to full-screen override
- No terminal/CLI interface needed — phone-only usage via Discord

### Visual color pass
- The entire display needs a color overhaul — currently too grey and monochrome
- Goal: both usable AND fun to look at — not just functional
- No specific color preferences — Claude designs a cohesive palette that works well on LED pixels
- Clock is currently too large and dominates the display — scale it down and rebalance zones
- Freed space distribution: Claude's discretion based on content needs
- Zone separators: Claude's discretion
- Date text color treatment: Claude's discretion
- Bus direction label colors: Claude's discretion
- Weather animations need color — rain drops, sun rays, etc. currently look grey/boring
- Animation colors: Claude picks vivid, LED-appropriate colors (to be tested and iterated)

### Birthday easter egg
- March 17 and December 16: special birthday display
- Crown/festive icon in top-right corner
- Additional festive touches beyond just the icon (festive text colors, etc.) — Claude designs the full birthday treatment
- Should be a fun surprise, not a dramatic takeover

### Claude's Discretion
- Transition style for brightness changes
- Config vs hardcoded for brightness schedule
- Staleness indicator visual approach
- Staleness timeout thresholds per data type
- Clock error detection (likely skip — not worth complexity)
- Zone rebalancing after clock resize
- Color palette design for the whole display
- Zone separator approach
- Date and label color treatments
- Weather animation color palette
- Birthday easter egg full design

</decisions>

<specifics>
## Specific Ideas

- "I want it to be both usable and something fun to look at" — not just functional grey
- Clock is too dominant — needs to shrink, zones should feel more balanced
- Messages are persistent reminders, not notifications — "Remember a bag for shopping" style
- User sends messages from phone only (Discord) — never from terminal
- Weather animations look boring when grey — need vivid colors for rain, sun, etc.
- Birthday dates: March 17 and December 16 — user loves the idea of festive treatment beyond just an icon

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-polish-and-reliability*
*Context gathered: 2026-02-20*
