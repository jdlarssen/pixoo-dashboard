---
phase: 02-bus-departures
verified: 2026-02-20T19:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 2: Bus Departures Verification Report

**Phase Goal:** Real-time bus departures from Ladeveien (both directions) populate the bus zone, refreshing every 60 seconds
**Verified:** 2026-02-20T19:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                      | Status     | Evidence                                                                              |
| --- | ------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------- |
| 1   | Next departures for direction 1 (Sentrum) from Ladeveien are displayed on screen          | VERIFIED   | `render_bus_zone()` draws `state.bus_direction1` at `BUS_ZONE.y + 1`; 8 renderer tests pass |
| 2   | Next departures for direction 2 (Lade) from Ladeveien are displayed on screen             | VERIFIED   | `render_bus_zone()` draws `state.bus_direction2` at `BUS_ZONE.y + 10`; tests confirm non-black pixels in bus zone |
| 3   | Departures show countdown format (bare minutes) rather than absolute time                  | VERIFIED   | `_draw_bus_line()` formats as bare integers (`str(departures[i])`); `fetch_departures()` computes `int((dep_time - now).total_seconds() / 60)` |
| 4   | Bus data refreshes every 60 seconds with updated countdowns                                | VERIFIED   | `main.py` lines 79-88: `last_bus_fetch = 0.0`, `time.monotonic()` comparison against `BUS_REFRESH_INTERVAL = 60` |
| 5   | Entur API is called with real Ladeveien quay IDs (not placeholder XXX)                    | VERIFIED   | `config.py`: `BUS_QUAY_DIRECTION1 = "NSR:Quay:73154"`, `BUS_QUAY_DIRECTION2 = "NSR:Quay:73152"` |
| 6   | API failures never crash the main loop                                                     | VERIFIED   | `fetch_departures_safe()` wraps all exceptions, logs, returns `None`; 2 error handling tests pass |
| 7   | DisplayState carries bus data for both directions and dirty flag pattern works              | VERIFIED   | `state.py` lines 21-22: `bus_direction1: tuple[int, ...] | None`, `bus_direction2: tuple[int, ...] | None`; equality tests confirm tuples compare correctly |
| 8   | Bus data refreshes independently from the 1-second display check                          | VERIFIED   | `main_loop()` uses separate `now_mono = time.monotonic()` timer; display check uses `datetime.now()` |

**Score:** 8/8 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact                    | Expected                                              | Exists | Substantive | Wired      | Status    |
| --------------------------- | ----------------------------------------------------- | ------ | ----------- | ---------- | --------- |
| `src/providers/bus.py`      | Entur API client with `fetch_departures()` and safe wrapper | Yes | Yes (140 lines, full implementation) | Imported in `main.py` and `renderer.py` via `config` | VERIFIED |
| `src/config.py`             | Bus configuration with env var overrides              | Yes    | Yes — `BUS_QUAY_DIRECTION1`, `BUS_QUAY_DIRECTION2`, `BUS_REFRESH_INTERVAL`, `BUS_NUM_DEPARTURES`, `ET_CLIENT_NAME`, `ENTUR_API_URL` | Imported in `bus.py`, `renderer.py`, `main.py` | VERIFIED |
| `src/display/state.py`      | `DisplayState` with `bus_direction1` and `bus_direction2` fields | Yes | Yes — both optional tuple fields present, `from_now()` accepts `bus_data` | Used in `main.py` and `renderer.py` | VERIFIED |
| `tests/test_bus_provider.py` | Tests for countdown calculation and response parsing | Yes | Yes — 17 tests across 5 test classes (countdown, cancellation, parsing, error handling, DisplayState) | All 17 pass | VERIFIED |

#### Plan 02 Artifacts

| Artifact                    | Expected                                              | Exists | Substantive | Wired      | Status    |
| --------------------------- | ----------------------------------------------------- | ------ | ----------- | ---------- | --------- |
| `src/display/layout.py`     | Bus zone color constants                              | Yes    | Yes — `COLOR_BUS_DIR1`, `COLOR_BUS_DIR2`, `COLOR_BUS_TIME` present | Imported in `renderer.py` | VERIFIED |
| `src/display/renderer.py`   | Bus zone rendering function `render_bus_zone()`       | Yes    | Yes — 95 lines, `render_bus_zone()` + `_draw_bus_line()` helper, full edge case handling | Called from `render_frame()` at line 138 | VERIFIED |
| `src/main.py`               | Main loop with independent 60-second bus fetch timer  | Yes    | Yes — `last_bus_fetch = 0.0`, monotonic clock comparison, `fetch_bus_data()` call, `DisplayState.from_now(now, bus_data=bus_data)` | Wired to provider and state | VERIFIED |
| `tests/test_renderer.py`    | Renderer tests verifying bus zone with departure data | Yes    | Yes — 8 bus zone tests in `TestBusZoneRendering` class covering: data, None, partial, zero, empty, long waits, size, save | All 8 pass | VERIFIED |

---

### Key Link Verification

#### Plan 01 Key Links

| From                   | To                                              | Via                                        | Status   | Evidence                                                             |
| ---------------------- | ----------------------------------------------- | ------------------------------------------ | -------- | -------------------------------------------------------------------- |
| `src/providers/bus.py` | `https://api.entur.io/journey-planner/v3/graphql` | `requests.post` with `ET-Client-Name` header | WIRED  | Line 77-82: `requests.post(ENTUR_API_URL, json={"query": query}, headers={"ET-Client-Name": ET_CLIENT_NAME}, timeout=10)` |
| `src/providers/bus.py` | `src/config.py`                                 | imports quay IDs and client name           | WIRED    | Lines 13-19: `from src.config import BUS_NUM_DEPARTURES, BUS_QUAY_DIRECTION1, BUS_QUAY_DIRECTION2, ENTUR_API_URL, ET_CLIENT_NAME` |
| `src/display/state.py` | `src/providers/bus.py`                          | `DisplayState.from_now` accepts bus data tuple | WIRED | Lines 26-45: `from_now(cls, dt, bus_data=(None, None))` converts lists to tuples at `bus_direction1/2` fields |

#### Plan 02 Key Links

| From                      | To                     | Via                                                 | Status | Evidence                                                              |
| ------------------------- | ---------------------- | --------------------------------------------------- | ------ | --------------------------------------------------------------------- |
| `src/display/renderer.py` | `src/display/state.py` | reads `bus_direction1` and `bus_direction2`        | WIRED  | Lines 47, 50: `state.bus_direction1`, `state.bus_direction2` passed to `_draw_bus_line()` |
| `src/display/renderer.py` | `src/display/layout.py` | uses `BUS_ZONE` coordinates and `COLOR_BUS` constants | WIRED | Lines 7-11: imports `BUS_ZONE, COLOR_BUS_DIR1, COLOR_BUS_DIR2, COLOR_BUS_TIME`; used at lines 47, 50, 94 |
| `src/main.py`             | `src/providers/bus.py` | calls `fetch_bus_data()` every 60 seconds           | WIRED  | Lines 32, 85-88: `from src.providers.bus import fetch_bus_data`; `bus_data = fetch_bus_data()` inside monotonic timer check |
| `src/main.py`             | `src/display/state.py` | passes `bus_data` tuple to `DisplayState.from_now()` | WIRED | Line 91: `current_state = DisplayState.from_now(now, bus_data=bus_data)` |

---

### Requirements Coverage

| Requirement | Source Plans  | Description                                         | Status    | Evidence                                                                   |
| ----------- | ------------- | --------------------------------------------------- | --------- | -------------------------------------------------------------------------- |
| BUS-01      | 02-01, 02-02  | Show next 2 departures from Ladeveien — direction 1 | SATISFIED | `render_bus_zone()` renders `state.bus_direction1`; `fetch_bus_data()` fetches from `NSR:Quay:73154`; implementation shows 3 (supersedes 2, user-requested upgrade) |
| BUS-02      | 02-01, 02-02  | Show next 2 departures from Ladeveien — direction 2 | SATISFIED | `render_bus_zone()` renders `state.bus_direction2`; `fetch_bus_data()` fetches from `NSR:Quay:73152`; implementation shows 3 (supersedes 2, user-requested upgrade) |
| BUS-03      | 02-01, 02-02  | Countdown format ("5 min" instead of "14:35")       | SATISFIED | `_draw_bus_line()` formats as bare integer minutes (e.g., "5 12 25"); no absolute clock times shown; "min" suffix omitted for display density on 64x64 — intent (non-absolute-time) met; confirmed acceptable on physical device |
| BUS-05      | 02-01, 02-02  | 60-second refresh cycle                             | SATISFIED | `BUS_REFRESH_INTERVAL = 60` in `config.py`; `main_loop()` uses `time.monotonic()` comparison; `last_bus_fetch = 0.0` triggers first fetch on startup |

**Orphaned requirements check:** BUS-04 (color coding by urgency) is mapped to Phase 4 in REQUIREMENTS.md traceability table — not claimed by this phase. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/display/renderer.py` | 146-151 | Weather zone renders placeholder `"VÆR"` text in `COLOR_PLACEHOLDER` | Info | Expected — Phase 3 not yet implemented; weather zone intentionally holds a dim placeholder |

No blocker or warning-level anti-patterns found. The weather placeholder is planned and expected.

---

### Human Verification Required

#### 1. Visual Readability on Physical Pixoo 64

**Test:** Run `python src/main.py --ip <PIXOO_IP>` and observe the bus zone from 2+ meters
**Expected:** Two direction lines visible — light blue `<S` label with 3 white countdown numbers, amber `>L` label with 3 white countdown numbers; numbers are legible at standing distance
**Why human:** Pixel-level readability and color visibility cannot be asserted by automated tests. The SUMMARY documents that this was verified during the Plan 02 checkpoint (user confirmed "approved"), so this item is considered CLOSED by the physical verification gate in Plan 02, Task 2.

#### 2. Live 60-Second Refresh Observed

**Test:** Watch terminal logs for `Bus data refreshed:` lines; verify countdown numbers decrease by ~1 each minute
**Expected:** Log line appears every ~60 seconds; bus zone numbers visibly tick down
**Why human:** Cannot assert timing behavior or live API data in automated tests. SUMMARY documents user observed this during checkpoint.

**Note:** Both human verification items were addressed by the blocking checkpoint in Plan 02, Task 2 ("verified working on physical Pixoo 64"). They are flagged here for completeness but are considered CLOSED by the checkpoint approval.

---

### Gaps Summary

No gaps. All automated checks pass, all artifacts are substantive and wired, all key links are connected, all four requirements are satisfied, and the physical device checkpoint was passed during execution.

**Notable deviation from plan (accepted):** BUS_NUM_DEPARTURES changed from 2 to 3 per user feedback during physical verification. Requirements BUS-01 and BUS-02 specify "next 2" — showing 3 is a superset that satisfies the stated requirement. REQUIREMENTS.md checkboxes already reflect this as Complete.

**BUS-03 format note:** The success criterion and requirement both reference "5 min" format. The implementation renders bare numbers ("5 12 25") without the "min" suffix. On a 64x64 display showing 3 numbers per line alongside a direction label, the suffix was omitted for density. The user confirmed the display was readable and acceptable during the blocking checkpoint. The requirement intent — showing elapsed countdown minutes rather than absolute departure times — is fully met.

---

_Verified: 2026-02-20T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
