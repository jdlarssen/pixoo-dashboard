# Phase 11: Discord Status Logging for Remote Monitoring - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Send application health and status information to a dedicated Discord channel so the device can be monitored remotely without SSH. The existing display-message channel behavior stays completely untouched. This phase adds monitoring as a purely additive capability.

</domain>

<decisions>
## Implementation Decisions

### What gets reported
- Problem alerting only — silent when healthy
- Startup and shutdown lifecycle messages
- Recovery messages when problems clear (e.g., "Weather API recovered after 23 minutes") with downtime duration
- No periodic heartbeats — silence means healthy

### Message format
- Rich Discord embeds with color-coding (red = error, green = recovery, blue = startup/info)
- Detail level: Claude's discretion, but errors should include enough context for `/gsd:debug` sessions — component, error type, duration, last success time
- Startup embed includes config summary (Pixoo IP, bus stop IDs, weather location)
- Recovery embeds include downtime duration

### Timing & triggers
- Claude decides debounce thresholds per error type (avoid noise from one-off blips)
- Claude designs repeat-suppression logic (no spamming the same error)
- No heartbeat — no periodic messages when healthy
- Optional via `DISCORD_MONITOR_CHANNEL_ID` env var — no channel configured = no monitoring, zero overhead

### Channel strategy
- Separate dedicated monitoring channel (configured via `DISCORD_MONITOR_CHANNEL_ID` in .env)
- Existing display-message channel completely untouched
- On-demand `status` command in monitoring channel returns a health snapshot (Claude designs what's included based on available data)
- Channel ID is sensitive — .env only, never committed

### Claude's Discretion
- Which specific errors are alert-worthy vs. ignorable
- Debounce thresholds and repeat-suppression intervals per error type
- On-demand status response content (based on available runtime data)
- Error embed detail level (enough for debugging sessions)
- Repeat-suppression reminder intervals

</decisions>

<specifics>
## Specific Ideas

- User wants error logs detailed enough to feed into `/gsd:debug` sessions — include component name, error type, timestamps, and context
- Monitoring channel ID is already known and will be set in .env
- The system already has staleness tracking for bus/weather data — leverage this for monitoring

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-discord-status-logging-for-remote-monitoring*
*Context gathered: 2026-02-23*
