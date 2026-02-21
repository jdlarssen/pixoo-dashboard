# Phase 2: Bus Departures - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Live bus departure countdowns from Ladeveien (both directions) rendered in the 64x19px bus zone, refreshing every 60 seconds. Displays next 2 departures per direction in countdown format. Urgency coloring is Phase 4 scope.

</domain>

<decisions>
## Implementation Decisions

### Bus zone layout
- Compact stacked: one line per direction, each line has direction label + 2 countdown numbers
- Two content lines total within the 19px tall bus zone
- Direction 1 (Sentrum) on top, direction 2 (Lade) below

### Direction labeling
- Arrow glyph + single letter: arrow + "S" for Sentrum, arrow + "L" for Lade
- Each direction gets a distinct color (different from each other) for the arrow+letter label
- Format example: `▶S  5  12` and `◀L  3  8`

### Countdown format
- Bare numbers only, no "min" or "m" suffix — context makes minutes obvious
- Two countdowns per line separated by spacing (next departure + following departure)

### Entur stop config
- Stop ID: `NSR:StopPlace:42686` (Ladeveien, Trondheim)
- Single stop serves both directions — use Entur direction/quay data to split departures
- Stop ID and direction config should be configurable via config file or environment variable, not hardcoded

### Claude's Discretion
- Separator between direction lines (thin divider vs spacing — pick what looks best in 19px)
- Visual distinction between first and second departure (brightness, color, or same style)
- Vertical alignment of content lines within bus zone (centered vs top-aligned)
- Arrow glyph style (filled triangle vs line arrow — pick what renders cleanly in BDF font)
- Direction label colors (pick two distinct, readable colors for LED display)
- "Now" indicator for 0-minute countdown (e.g., "Nå" vs "0")
- No-bus empty state (dashes, blank, or message — pick best approach for the display)
- Long wait handling (cap at 60+, show raw number, or switch to clock time)

</decisions>

<specifics>
## Specific Ideas

- "Arrow + S/L" labeling was the user's idea — keep it compact and recognizable
- Different colors per direction to help distinguish at a glance from across the room
- Numbers-only countdown keeps the line short enough to fit direction label + 2 departures in 64px width

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-bus-departures*
*Context gathered: 2026-02-20*
