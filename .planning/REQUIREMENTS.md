# Requirements: Divoom Hub

**Defined:** 2026-02-20
**Core Value:** Glance at the display and instantly know: what time it is, when the next buses leave, and what the weather is doing — without pulling out your phone.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Display

- [x] **DISP-01**: Full-frame custom rendering via PIL/Pillow pushed to Pixoo 64
- [x] **DISP-02**: Pixel font rendering with Norwegian character support (æøå)
- [x] **DISP-03**: Single-screen layout — all info zones on 64x64, readable at a glance
- [ ] **DISP-04**: Auto-brightness based on time of day

### Clock

- [x] **CLCK-01**: Display current time in large, readable digits
- [x] **CLCK-02**: Display today's date in Norwegian (e.g. "tor 20. feb")

### Bus

- [x] **BUS-01**: Show next 2 departures from Ladeveien — direction 1
- [x] **BUS-02**: Show next 2 departures from Ladeveien — direction 2
- [x] **BUS-03**: Countdown format ("5 min" instead of "14:35")
- [ ] **BUS-04**: Color coding by urgency (green/yellow/red)
- [x] **BUS-05**: 60-second refresh cycle

### Weather

- [x] **WTHR-01**: Current temperature (°C) from Yr/MET
- [ ] **WTHR-02**: Weather icon as pixel art sprite
- [x] **WTHR-03**: Today's high/low temperature
- [x] **WTHR-04**: Rain expected indicator

### Reliability

- [x] **RLBL-01**: Connection refresh cycle (prevent 300-push lockup)
- [ ] **RLBL-02**: Graceful error states (show last known data when API fails)
- [ ] **RLBL-03**: Auto-restart via service wrapper (systemd/launchd)

### Messages

- [ ] **MSG-01**: Push text message to temporarily override display

## v2 Requirements

### Display Enhancements

- **DISP-05**: Smooth transitions between frame updates
- **DISP-06**: Blinking colon separator on clock

### Bus Enhancements

- **BUS-06**: Real-time vs scheduled departure indicator

### Weather Enhancements

- **WTHR-05**: Next-hour precipitation forecast
- **WTHR-06**: Wind speed/direction

### Messages Enhancements

- **MSG-02**: Priority levels (urgent = interrupt, info = show on next refresh)
- **MSG-03**: Auto-dismiss after configurable timeout

### Reliability Enhancements

- **RLBL-04**: Network reconnection handling (WiFi drop recovery)
- **RLBL-05**: API health monitoring / dashboard

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Headless service — no UI beyond the Pixoo display |
| Multi-device support | Single Pixoo 64 in the entryway |
| Historical data / logging | Not useful for a glance-dashboard |
| Complex animations | Readability over flash — 64x64 demands simplicity |
| Native Pixoo text commands | Can't coexist with custom rendering; no æøå support |
| Route number display | Only one bus route at Ladeveien — not needed |
| Seconds display on clock | Wastes pixels, minimal value for an entryway glance |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISP-01 | Phase 1 | Complete |
| DISP-02 | Phase 1 | Complete |
| DISP-03 | Phase 1 | Complete |
| DISP-04 | Phase 4 | Pending |
| CLCK-01 | Phase 1 | Complete |
| CLCK-02 | Phase 1 | Complete |
| BUS-01 | Phase 2 | Complete |
| BUS-02 | Phase 2 | Complete |
| BUS-03 | Phase 2 | Complete |
| BUS-04 | Phase 4 | Pending |
| BUS-05 | Phase 2 | Complete |
| WTHR-01 | Phase 3 | Complete |
| WTHR-02 | Phase 3 | Pending |
| WTHR-03 | Phase 3 | Complete |
| WTHR-04 | Phase 3 | Complete |
| RLBL-01 | Phase 1 | Complete |
| RLBL-02 | Phase 4 | Pending |
| RLBL-03 | Phase 4 | Pending |
| MSG-01 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-02-20*
*Last updated: 2026-02-20 after roadmap creation*
