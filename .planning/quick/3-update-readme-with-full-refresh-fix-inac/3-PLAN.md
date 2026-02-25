---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [README.md]
autonomous: true
requirements: [README-REFRESH]

must_haves:
  truths:
    - "Clone URL points to jdlarssen/pixoo-dashboard"
    - "Architecture tree includes discord_monitor.py"
    - "Optional env vars table includes DISCORD_MONITOR_CHANNEL_ID"
    - "Rate limiting correctly states 1.0 sekund"
    - "Animation FPS correctly states ~1 FPS (1.0s) everywhere"
    - "Feilhaandtering section documents keep-alive, backoff, and auto-reboot"
    - "Dataflyt diagram reflects ping/reboot/backoff loop"
  artifacts:
    - path: "README.md"
      provides: "Accurate, up-to-date project documentation in Norwegian"
  key_links: []
---

<objective>
Update README.md with 7 specific corrections and additions: fix clone URL, add discord_monitor.py to architecture tree, add DISCORD_MONITOR_CHANNEL_ID to env vars, fix rate limiting value, fix animation FPS values, add resilience subsection to Feilhaandtering, and update the Dataflyt diagram.

Purpose: README currently has stale values from earlier development (0.3s rate limit, 3 FPS) and is missing features added in v1.2 (discord_monitor, keep-alive ping, exponential backoff, auto-reboot).
Output: Single updated README.md with all 7 fixes applied.
</objective>

<execution_context>
@/Users/jdl/.claude/get-shit-done/workflows/execute-plan.md
@/Users/jdl/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@README.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Apply all 7 README corrections and additions</name>
  <files>README.md</files>
  <action>
Apply these 7 edits to README.md. Keep all existing Norwegian language. Do NOT change anything else.

**1. Clone URL (line 75):**
Change `https://github.com/YOUR_USERNAME/divoom-hub.git` to `https://github.com/jdlarssen/pixoo-dashboard.git`

**2. Architecture tree (line 242 area, under providers/):**
Add `discord_monitor.py` entry after `discord_bot.py`:
```
    ├── discord_monitor.py  # Helseovervaakning og statusrapportering (Discord-embeds)
```

**3. Env vars table (line 110 area, in Valgfrie variabler table):**
Add row after `DISCORD_CHANNEL_ID`:
```
| `DISCORD_MONITOR_CHANNEL_ID` | Discord-kanal-ID for statusovervaakning | *(deaktivert)* |
```
Also add to the .env-eksempel inside the details block (after line 135):
```
# DISCORD_MONITOR_CHANNEL_ID=123456789012345678
```

**4. Rate limiting (line 397 area):**
Change "minimum 0.3 sekunder mellom hvert bilde" to "minimum 1.0 sekund mellom hvert bilde"

**5. Animation FPS -- two locations:**
- Line 253 area (Dataflyt): Change `~3 FPS` to `~1 FPS` in the `weather_anim.tick()` line
- Line 360 area (Vaeranimasjoner section): Change "~3 FPS (0.35s mellom hvert bilde)" to "~1 FPS (1.0s mellom hvert bilde)"
- Line 261 area (To hastigheter paragraph): Change "0.35s pause (~3 FPS)" to "1.0s pause (~1 FPS)" AND change "sover den 1 sekund" -- this sentence should be updated to reflect that both speeds are now 1.0s. Rewrite the paragraph to: "Hovedloopen kjorer med 1.0s pause mellom hver iterasjon. Naar vaeranimasjon er aktiv oppdateres animasjonsbildet hver iterasjon (~1 FPS). Naar det er stille vaer, sjekker loopen kun om tilstanden har endret seg."

**6. New resilience subsection in Feilhaandtering (after the Enhetstilkobling bullet section, before Auto-lysstyrke):**
Add a new subsection:

```
**Resiliens (keep-alive og gjenoppretting):**
- **Keep-alive ping:** Hvert 30. sekund sender klienten en lettvekts ping (`Channel/GetAllConf`) til enheten for aa forhindre at WiFi-stroemsparingsmodus kobler fra
- **Eksponentiell backoff:** Ved kommunikasjonsfeil starter en venteperiode paa 3 sekunder som dobles for hver paafølgende feil (3s -> 6s -> 12s -> 24s -> ...) opp til maks 60 sekunder. Tilbakestilles til 3s ved første vellykkede kommunikasjon
- **Auto-reboot:** Etter 5 sammenhengende enhetsfeil sendes en `Device/SysReboot`-kommando. Deretter venter systemet 30 sekunder for at enheten skal koble seg til igjen foer normal drift gjenopptas
- Alle tre mekanismene virker sammen: ping oppdager problemer tidlig, backoff forhindrer overbelastning av en treg enhet, og reboot er siste utvei naar ingenting annet fungerer
```

**7. Dataflyt diagram (line 250 area):**
Update the diagram to include the resilience loop. Replace the existing diagram with:

```
main_loop()
  ├── fetch_bus_data()         -> Entur GraphQL API (hvert 60. sekund)
  ├── fetch_weather_safe()     -> MET Norway API (hvert 600. sekund)
  ├── weather_anim.tick()      -> bg/fg RGBA-lag (~1 FPS)
  ├── DisplayState.from_now()  -> dirty flag-sjekk
  ├── render_frame()           -> 64x64 PIL-bilde
  ├── client.push_frame()      -> Pixoo 64 via HTTP
  │     ├── OK                 -> oppdater last_device_success
  │     └── Feil               -> eksponentiell backoff (3s -> 60s)
  └── keep-alive (hvert 30s)
        ├── client.ping()      -> lettvekts helsesjekk
        └── 5 feil paa rad     -> client.reboot() + 30s ventetid
```

IMPORTANT: Use proper Norwegian special characters (ae, oe, aa as appropriate for the context -- the existing README uses actual ae, oe, aa Unicode characters). Match the existing style exactly.
  </action>
  <verify>
    <automated>cd /Users/jdl/Documents/GitHub/divoom-hub && python -c "
import sys
r = open('README.md').read()
checks = [
    ('jdlarssen/pixoo-dashboard' in r, 'Clone URL updated'),
    ('discord_monitor.py' in r, 'discord_monitor.py in architecture'),
    ('DISCORD_MONITOR_CHANNEL_ID' in r, 'DISCORD_MONITOR_CHANNEL_ID in env vars'),
    ('1.0 sekund' in r, 'Rate limiting fixed to 1.0'),
    ('0.3 sekund' not in r, 'Old 0.3s value removed'),
    ('~1 FPS' in r, 'FPS updated to ~1'),
    ('~3 FPS' not in r, 'Old 3 FPS removed'),
    ('0.35s' not in r, 'Old 0.35s removed'),
    ('keep-alive' in r.lower() or 'Keep-alive' in r, 'Keep-alive documented'),
    ('backoff' in r.lower() or 'Backoff' in r, 'Backoff documented'),
    ('reboot' in r.lower() or 'Reboot' in r, 'Auto-reboot documented'),
    ('YOUR_USERNAME' not in r, 'Placeholder username removed'),
]
failed = [msg for ok, msg in checks if not ok]
if failed:
    print('FAILED checks:')
    for f in failed: print(f'  - {f}')
    sys.exit(1)
print('All 12 checks passed')
"
    </automated>
  </verify>
  <done>README.md contains all 7 corrections: correct clone URL, discord_monitor.py in tree, DISCORD_MONITOR_CHANNEL_ID in env table, 1.0s rate limit, ~1 FPS animation speed, resilience subsection with keep-alive/backoff/reboot details, and updated Dataflyt diagram showing the resilience loop.</done>
</task>

</tasks>

<verification>
All 7 approved changes applied to README.md. No other files modified. Norwegian language maintained throughout. Values match actual source code constants.
</verification>

<success_criteria>
- Clone URL: `jdlarssen/pixoo-dashboard`
- Architecture tree: `discord_monitor.py` listed under providers
- Env vars: `DISCORD_MONITOR_CHANNEL_ID` in optional table and .env example
- Rate limiting: "1.0 sekund" (not "0.3 sekunder")
- Animation: "~1 FPS" and "1.0s" (not "~3 FPS" or "0.35s")
- Resilience: New subsection documenting ping (30s), backoff (3s base, 60s cap, doubles), reboot (5 failures, 30s wait)
- Dataflyt: Diagram shows ping/reboot/backoff flow
</success_criteria>

<output>
After completion, create `.planning/quick/3-update-readme-with-full-refresh-fix-inac/3-SUMMARY.md`
</output>
