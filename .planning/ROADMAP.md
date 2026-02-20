# Roadmap: Divoom Hub

## Overview

Divoom Hub delivers an always-on entryway dashboard on a 64x64 LED pixel display. The build order follows the rendering pipeline bottom-up: first establish device communication, the pixel render engine, and the layout with clock/date (the visual foundation everything else sits on); then integrate bus departures (the highest-urgency data source); then weather (the second data source with stricter API constraints); then layer on reliability hardening, UX polish, and the message override feature. Each phase delivers a verifiably working dashboard with progressively richer information.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Device driver, render engine, pixel layout, and clock/date on the Pixoo 64
- [ ] **Phase 2: Bus Departures** - Live Entur transit data for Ladeveien in both directions
- [ ] **Phase 3: Weather** - Yr/MET weather data with pixel art icons
- [ ] **Phase 4: Polish and Reliability** - Urgency coloring, brightness, error handling, service wrapper, and push messages

## Phase Details

### Phase 1: Foundation
**Goal**: A working 64x64 dashboard frame displaying accurate time and Norwegian date, pushed to the Pixoo 64 and running sustainably without device lockup
**Depends on**: Nothing (first phase)
**Requirements**: DISP-01, DISP-02, DISP-03, CLCK-01, CLCK-02, RLBL-01
**Success Criteria** (what must be TRUE):
  1. The Pixoo 64 displays a custom-rendered 64x64 frame composed via PIL/Pillow
  2. Current time is shown in large, readable digits (legible from 2+ meters)
  3. Today's date appears in Norwegian with correct characters (e.g. "tor 20. feb" with working ae/oe/aa)
  4. All planned information zones (clock, bus, weather) are visible and proportioned on a single screen
  5. The display runs continuously for 8+ hours without device lockup (connection refresh working)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffolding, BDF font system, and Pixoo device client
- [ ] 01-02-PLAN.md — Norwegian clock, zone layout, renderer, main loop, and device verification

### Phase 2: Bus Departures
**Goal**: Real-time bus departures from Ladeveien (both directions) populate the bus zone, refreshing every 60 seconds
**Depends on**: Phase 1
**Requirements**: BUS-01, BUS-02, BUS-03, BUS-05
**Success Criteria** (what must be TRUE):
  1. Next 2 bus departures for direction 1 from Ladeveien are displayed on screen
  2. Next 2 bus departures for direction 2 from Ladeveien are displayed on screen
  3. Departures show countdown format ("5 min") rather than absolute time
  4. Bus data refreshes every 60 seconds with updated countdowns
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: Weather
**Goal**: Current weather conditions from Yr fill the weather zone with temperature, icon, and forecast data
**Depends on**: Phase 2
**Requirements**: WTHR-01, WTHR-02, WTHR-03, WTHR-04
**Success Criteria** (what must be TRUE):
  1. Current temperature in Celsius is displayed from Yr/MET data
  2. A pixel art weather icon (sun, clouds, rain, etc.) correctly represents current conditions
  3. Today's high and low temperatures are visible
  4. A rain indicator is shown when precipitation is expected
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Polish and Reliability
**Goal**: The dashboard is production-quality for daily use with urgency coloring, adaptive brightness, robust error handling, supervised operation, and message override capability
**Depends on**: Phase 3
**Requirements**: DISP-04, BUS-04, RLBL-02, RLBL-03, MSG-01
**Success Criteria** (what must be TRUE):
  1. Bus departures are color-coded by urgency (green for plenty of time, yellow for hurry, red for imminent)
  2. Display brightness adjusts automatically based on time of day (dim at night, bright during day)
  3. When an API fails, the display shows last known data with a visible staleness indicator rather than crashing or going blank
  4. The service restarts automatically after a crash or system reboot (systemd/launchd wrapper)
  5. A text message can be pushed to temporarily override the normal display
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planned | - |
| 2. Bus Departures | 0/? | Not started | - |
| 3. Weather | 0/? | Not started | - |
| 4. Polish and Reliability | 0/? | Not started | - |
