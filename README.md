# Divoom Hub

> Alltid-på LED-dashbord for Pixoo 64 -- klokke, bussavganger og vær med et blikk.

[![Bygget med Claude Code](https://img.shields.io/badge/Bygget_med-Claude_Code-orange?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/code)

<!-- Bytt ut bildet nedenfor med et ekte foto av displayet ditt.
     Legg bildet i docs/display-photo.jpg (eller endre stien). -->
![Pixoo 64-dashbordet i aksjon](docs/display-photo.jpg)

Et personlig hjemmedashbord som kjører på en Divoom Pixoo 64 LED-skjerm. Med et raskt blikk på displayet ser du hva klokka er, når neste buss går, og hvordan været er -- uten å ta opp telefonen.

Prosjektet er bygget som et hobbyprosjekt for eget bruk. Displayet står på en hylle og viser sanntidsdata døgnets 24 timer: klokke med norsk dato, bussavganger fra to retninger med nedtelling i farger (grønn, gul, rød), værmelding med animerte overlegg (regn, snø, sol, torden, tåke), og en valgfri Discord-meldingsfunksjon for å sende korte beskjeder til skjermen.

Alt er skrevet i Python og snakker med Pixoo 64 over lokalnettverket. Værdata kommer fra MET Norway (yr.no-backend), bussdata fra Entur, og klokka formateres på norsk med æ, ø og å.

---

## Displayoppsett (64x64 piksler)

Displayet er delt inn i seks soner som fyller hele 64x64-skjermen:

```
+----------------------------------------------------------------+
|  14:32  [sol]                                           KLOKKE  |  y 0-10
|  tor 20. feb                                              DATO  |  y 11-18
|----------------------------------------------------------------|  y 19
|  <S  5  12  25                                            BUSS  |  y 20-29
|  >L  3   8  18                                            BUSS  |  y 30-38
|----------------------------------------------------------------|  y 39
|  7   2.3mm                                                 VÆR  |  y 40-49
|  5/2          ~~~                                               |  y 50-58
|                ~~~                                              |  y 59-63
+----------------------------------------------------------------+
```

| Sone | Y-start | Y-slutt | Høyde | Innhold |
|------|---------|---------|-------|---------|
| Klokke | 0 | 10 | 11 px | HH:MM i 24-timers format + værikon |
| Dato | 11 | 18 | 8 px | Norsk dato, f.eks. "tor 20. feb" |
| Skillelinje | 19 | 19 | 1 px | Tynn teal-strek |
| Buss | 20 | 38 | 19 px | To retninger med fargekodede nedtellinger |
| Skillelinje | 39 | 39 | 1 px | Tynn teal-strek |
| Vær | 40 | 63 | 24 px | Temperatur, høy/lav, nedbør, animasjon |

**Bussnedtelling i farger:**
- Grønn: > 10 min (god tid)
- Gul: 5--10 min (skynd deg)
- Rød: < 5 min (snart borte)
- Dimmet: < 2 min (bussen er i praksis borte)

---

## Forutsetninger

- **Python 3.10+**
- **Divoom Pixoo 64** på samme lokalnettverk (LAN)
- Internettforbindelse for vær- og buss-API-er

Avhengigheter (installeres automatisk):

| Pakke | Versjon | Formål |
|-------|---------|--------|
| pixoo | -- | Kommunikasjon med Pixoo 64 |
| Pillow | >= 12.1.0 | Bildebehandling og fontrendering |
| astral | >= 3.2 | Astronomisk soloppgang/solnedgang for auto-lysstyrke |
| discord.py | >= 2.0 | Valgfri Discord-meldingsoverstyring |
| python-dotenv | >= 1.0 | Lasting av .env-konfigurasjon |

---

## Installasjon

```bash
git clone https://github.com/jdlarssen/pixoo-dashboard.git
cd divoom-hub
python -m venv .venv
source .venv/bin/activate
pip install .
```

For utvikling (pytest + ruff):

```bash
pip install ".[dev]"
```

---

## Konfigurasjon

Kopier `.env.example` til `.env` og fyll inn dine verdier:

```bash
cp .env.example .env
```

### Påkrevde variabler

| Variabel | Beskrivelse | Eksempel |
|----------|-------------|----------|
| `DIVOOM_IP` | IP-adressen til Pixoo 64 på LAN | `192.168.1.100` |
| `BUS_QUAY_DIR1` | Entur quay-ID for retning 1 | `NSR:Quay:XXXXX` |
| `BUS_QUAY_DIR2` | Entur quay-ID for retning 2 | `NSR:Quay:XXXXX` |
| `WEATHER_LAT` | Breddegrad (desimalgrader) | `59.9139` |
| `WEATHER_LON` | Lengdegrad (desimalgrader) | `10.7522` |

Finn dine quay-ID-er på [stoppested.entur.org](https://stoppested.entur.org) og koordinater på [latlong.net](https://www.latlong.net).

### Valgfrie variabler

| Variabel | Beskrivelse | Standard |
|----------|-------------|----------|
| `ET_CLIENT_NAME` | Identifiserer appen mot Entur API | `pixoo-dashboard` |
| `WEATHER_USER_AGENT` | User-Agent for MET Norway API (påbudt) | `pixoo-dashboard/1.0` |
| `DISCORD_BOT_TOKEN` | Discord-bot-token for meldingsoverstyring | *(deaktivert)* |
| `DISCORD_CHANNEL_ID` | Discord-kanal-ID for meldinger | *(deaktivert)* |
| `DISCORD_MONITOR_CHANNEL_ID` | Discord-kanal-ID for statusovervåkning | *(deaktivert)* |
| `BIRTHDAY_DATES` | Bursdagsdatoer for easter egg (MM-DD, kommaseparert) | *(ingen)* |

<details>
<summary>Komplett .env-eksempel</summary>

```bash
# === PÅKREVD ===
DIVOOM_IP=192.168.1.100
BUS_QUAY_DIR1=NSR:Quay:XXXXX
BUS_QUAY_DIR2=NSR:Quay:XXXXX
WEATHER_LAT=59.9139
WEATHER_LON=10.7522

# === VALGFRITT ===
# ET_CLIENT_NAME=mitt-pixoo-dashbord
# WEATHER_USER_AGENT=pixoo-dashboard/1.0 epost@eksempel.no
# DISCORD_BOT_TOKEN=din-bot-token-her
# DISCORD_CHANNEL_ID=123456789012345678
# DISCORD_MONITOR_CHANNEL_ID=123456789012345678
# BIRTHDAY_DATES=01-01,06-15
```

</details>

---

## Bruk

```bash
# Standard kjøring (krever Pixoo 64 på nettverket)
python src/main.py

# Med egendefinert IP-adresse
python src/main.py --ip 192.168.1.100

# Simulatormodus (ingen maskinvare -- åpner Tkinter-vindu)
python src/main.py --simulated

# Debug-modus (lagrer hvert bilde til debug_frame.png)
python src/main.py --save-frame

# Test væranimasjon (kombineres gjerne med --simulated)
TEST_WEATHER=rain python src/main.py --simulated
```

Tilgjengelige værtyper for `TEST_WEATHER`: `clear`, `rain`, `snow`, `fog`, `cloudy`, `sun`, `thunder`

---

## Kjøre som tjeneste (macOS launchd)

Prosjektet inkluderer en ferdig `com.divoom-hub.dashboard.plist` for automatisk oppstart.

<details>
<summary>Steg-for-steg oppsett</summary>

**1. Rediger stier i plist-filen**

Åpne `com.divoom-hub.dashboard.plist` og erstatt `/EDIT/PATH/TO/` med den faktiske stien til prosjektet. Oppdater også IP-adressen til din Pixoo 64.

**2. Kopier til LaunchAgents**

```bash
cp com.divoom-hub.dashboard.plist ~/Library/LaunchAgents/
```

**3. Last inn tjenesten**

```bash
launchctl load ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist
```

**4. Sjekk status**

```bash
launchctl list | grep divoom
```

**5. Stopp tjenesten**

```bash
launchctl unload ~/Library/LaunchAgents/com.divoom-hub.dashboard.plist
```

**6. Se logger**

```bash
tail -f /tmp/divoom-hub.log
tail -f /tmp/divoom-hub.err
```

Tjenesten starter automatisk ved innlogging og restarter ved krasj (men ikke ved ren avslutning).

</details>

---

## Bygget med Claude Code

Dette prosjektet ble bygget fra bunnen av med [Claude Code](https://claude.ai/code) -- Anthropics CLI-verktøy for AI-assistert utvikling. Fra første linje Python til siste piksel på displayet har Claude vært utviklingspartneren.

Hele prosessen fulgte en strukturert arbeidsflyt: kravdefinisjon, arkitekturplanlegging, implementering i faser, testing og verifisering -- alt drevet av samtaler med Claude. Prosjektet gikk fra idé til ferdig dashbord på en enkelt dag.

Det er ikke et eksperiment i "la AI skrive all koden" -- det er et samarbeidsprosjekt der et menneske definerte hva som skulle bygges, tok designbeslutninger og validerte resultatene, mens Claude stod for implementeringen, feilsøking og testing.

---

## Arkitektur

```
src/
├── main.py              # Hovedloop, CLI-argumenter, datahenting
├── config.py             # All konfigurasjon (.env-lasting, konstanter)
├── device/
│   └── pixoo_client.py   # Pixoo 64-kommunikasjon med rate limiting
├── display/
│   ├── fonts.py          # BDF-fontlasting og konvertering
│   ├── layout.py         # Sonedefinisjon, farger, pikselkoordinater
│   ├── renderer.py       # PIL-kompositor (state -> 64x64-bilde)
│   ├── state.py          # DisplayState med dirty flag-mønster
│   ├── weather_anim.py   # 8 animasjonstyper med dybdelag
│   └── weather_icons.py  # Pikselkunst-værikon (10x10 px)
└── providers/
    ├── bus.py            # Entur JourneyPlanner v3 (GraphQL)
    ├── clock.py          # Norsk tid- og datoformatering
    ├── discord_bot.py    # Discord-meldingsoverstyring (daemon-tråd)
    ├── discord_monitor.py  # Helseovervåkning og statusrapportering (Discord-embeds)
    ├── sun.py            # Astronomisk soloppgang/solnedgang (astral)
    └── weather.py        # MET Norway Locationforecast 2.0
```

### Dataflyt

```
main_loop()
  ├── fetch_bus_data()         → Entur GraphQL API (hvert 60. sekund)
  ├── fetch_weather_safe()     → MET Norway API (hvert 600. sekund)
  ├── weather_anim.tick()      → bg/fg RGBA-lag (~1 FPS)
  ├── DisplayState.from_now()  → dirty flag-sjekk
  ├── render_frame()           → 64x64 PIL-bilde
  ├── client.push_frame()      → Pixoo 64 via HTTP
  │     ├── OK                 → oppdater last_device_success
  │     └── Feil               → eksponentiell backoff (3s → 60s)
  └── keep-alive (hvert 30s)
        ├── client.ping()      → lettvekts helsesjekk
        └── 5 feil på rad      → client.reboot() + 30s ventetid
```

**Dirty flag-mønsteret:** `DisplayState` er en dataklasse med likhetskontroll. Hovedloopen sammenligner forrige og nåværende tilstand -- bildet rendres kun på nytt når noe faktisk har endret seg (nytt minutt, nye bussdata, nytt vær).

**To hastigheter:** Hovedloopen kjører med 1.0s pause mellom hver iterasjon. Når væranimasjon er aktiv oppdateres animasjonsbildet hver iterasjon (~1 FPS). Når det er stille vær, sjekker loopen kun om tilstanden har endret seg.

---

## API-er

<details>
<summary>Entur JourneyPlanner v3 (bussdata)</summary>

**Endepunkt:** `https://api.entur.io/journey-planner/v3/graphql`

**Påbudt header:** `ET-Client-Name` -- identifiserer appen din mot Entur.

Appen sender et GraphQL-query som henter `estimatedCalls` for en gitt quay-ID. Hver avgang gir `expectedDepartureTime` (sanntid når tilgjengelig), `aimedDepartureTime`, `realtime`-flagg, og destinasjonsinfo.

**Gotchas:**
- Kansellerte avganger finnes i svaret -- appen filtrerer dem bort og ber om ekstra avganger for å kompensere
- Tidsberegning: `expectedDepartureTime` er ISO 8601 med tidssone, konverteres til nedtellingsminutter med `datetime.fromisoformat()`
- Nedtelling klippes til minimum 0 (ingen negative verdier)

</details>

<details>
<summary>MET Norway Locationforecast 2.0 (værdata)</summary>

**Endepunkt:** `https://api.met.no/weatherapi/locationforecast/2.0/compact`

**Påbudt header:** `User-Agent` -- MET krever identifikasjon per bruksvilkår.

Appen bruker `If-Modified-Since`-caching: første kall laster ned full respons, deretter sendes `Last-Modified`-verdien tilbake. MET returnerer `304 Not Modified` når data er uendret, noe som sparer bandbredde og respekterer API-vilkårene. Cachen lagres på modulnivå i Python.

**Svaret inneholder:**
- `timeseries` med værdata per tidspunkt
- Hvert tidspunkt har `instant` (nåværende), `next_1_hours` og `next_6_hours` prognoser
- `symbol_code` (f.eks. `clearsky_day`, `rain_night`) brukes for ikon- og animasjonsvalg

**Gotchas:**
- Høy/lav-temperatur er ikke et eget felt -- appen skanner alle tidspunkter for dagens dato og finner maks/min
- `symbol_code` har suffikser (`_day`, `_night`, `_polartwilight`) som må strippes for ikonoppslag
- API-et oppdateres omtrent hvert 10. minutt

</details>

---

## Discord-meldingsoverstyring

En valgfri Discord-bot lar deg sende korte meldinger til displayet. Boten kjører i en bakgrunnstråd (daemon) og er helt uavhengig av hovedloopen.

**Oppsett:**
1. Opprett en Discord-bot på [discord.com/developers](https://discord.com/developers/applications)
2. Aktiver "Message Content Intent"
3. Inviter boten til en server og en kanal
4. Legg til `DISCORD_BOT_TOKEN` og `DISCORD_CHANNEL_ID` i `.env`

**Bruk:**
- Skriv en melding i kanalen -- den vises i værsonen på displayet
- Skriv `clear`, `cls` eller `reset` for å fjerne meldingen
- Boten reagerer med et avkrysningsmerke for å bekrefte mottak

Meldingen vises i nedre del av værsonen (under temperatur og høy/lav). Når en melding er aktiv, skjules nedbørsindikatoren for å gi plass.

Hvis `DISCORD_BOT_TOKEN` eller `DISCORD_CHANNEL_ID` ikke er satt, starter boten rett og slett ikke -- ingen feilmelding, ingen påvirkning på dashbordet.

---

## Væranimasjoner

Værsonen (24 piksler høy) har animerte overlegg som gir liv til displayet. Systemet bruker et 3D-dybdeeffekt med to lag:

- **Bakgrunnslag** (bak tekst): fjerne, dimmere partikler
- **Forgrunnslag** (foran tekst): nære, lysere partikler

Hvert bilde rendres ved å legge bakgrunnslaget under teksten og forgrunnslaget over -- dette skaper en illusjon av dybde på en flat 64x64-skjerm.

<details>
<summary>De 8 animasjonstypene</summary>

| Type | Beskrivelse |
|------|-------------|
| **Regn** | Blå dråper i to dybder -- fjerne dråper er dimmere og kortere, nære er lysere med 3px streker |
| **Snø** | Krystaller i + form (nære, lyse) og enkeltpiksler (fjerne, dimme) som driver sakte |
| **Sol** | Diagonale gylne solstråler som faller nedover i to hastigheter |
| **Skyer** | Grå-hvite skyellipser som driver sakte gjennom sonen |
| **Torden** | Regn + lyn hvert ~4. sekund med 3-bilders syklus (blink, etterglød, fade) |
| **Tåke** | Skyblober som driver gjennom høyre side av sonen |
| **Delvis skyet** | Samme som sol |
| **Sludd** | Samme som regn |

</details>

### Lagdelte animasjoner og vindeffekt

Animasjonssystemet støtter sammensatte effekter når værforholdene tilsier det:

- **Intensitetsskalering:** Snø- og regnanimasjoner tilpasser antall partikler etter nedbørsmengde (lett < 1mm, moderat 1--3mm, kraftig > 3mm, ekstrem > 5mm)
- **Vindeffekt:** Når det blåser legges en horisontal drift på partiklene basert på faktisk vindretning og vindstyrke fra MET API
- **Kombo-regler:** Kraftig regn (> 3mm) legger automatisk tåke oppå regnet. Torden og regn med sterk vind (> 5 m/s) får vinddrift. Snø med vind > 3 m/s driver sidelengs.

Animasjonene kjører med ~1 FPS (1.0s mellom hvert bilde). Alpha-verdier er tunet for LED-maskinvarens synlighet (65--180-området).

---

## Norske tegn og fonter

Displayet bruker BDF-bitmap-fonter i tre størrelser:

| Font | Størrelse | Brukes til |
|------|-----------|-----------|
| 4x6 | 4x6 px | Høy/lav-temperatur, nedbør, meldinger |
| 5x8 | 5x8 px | Klokke, dato, bussnedtellinger |
| 7x13 | 7x13 px | Tilgjengelig, ikke i bruk |

Fontene lastes fra `assets/fonts/`-mappen. BDF-filene konverteres automatisk til PIL-format (`.pil` + `.pbm`) ved første kjøring -- disse genererte filene er i `.gitignore`.

Norske spesialtegn (æ, ø, å) finnes i BDF-fontene og brukes i dagsnavn: **lørdag** og **søndag** inneholder ø. Klokkeleverandøren (`clock.py`) bruker egne norske ordbokoppslag for dag- og månedsnavn istedenfor systemets locale -- dette unngår avhengighet på installert språkstøtte.

---

## Feilhåndtering

Dashbordet er designet for å kjøre døgnkontinuerlig uten tilsyn. Flere lag med feilhåndtering holder det stabilt:

**Staleness-sporing (foreldet data):**

| Datakilde | Stale (aldrende) | For gammel (vises ikke) |
|-----------|-------------------|------------------------|
| Buss | > 3 min | > 10 min |
| Vær | > 30 min | > 1 time |

- Når data er *stale* men brukbar: vises med en oransje prikk øverst i høyre hjørne av sonen
- Når data er *for gammel*: erstattes med `--` plassholdere
- Ved API-feil: siste vellykkede data beholdes og vises videre

**Enhetstilkobling:**
- `pixoo`-bibliotekets `refresh_connection_automatically` forhindrer at tilkoblingen låser seg etter ~300 push-operasjoner
- Rate limiting: minimum 1.0 sekund mellom hvert bilde (forhindrer tapte frames ved timing-jitter)
- Lysstyrke begrenset til 90% (`MAX_BRIGHTNESS`) -- full lysstyrke kan krasje enheten
- Nettverksfeil (timeout, tilkoblingsbrudd) fanges opp og logges -- dashbordet fortsetter å kjøre og prøver igjen neste iterasjon

**Resiliens (keep-alive og gjenoppretting):**
- **Keep-alive ping:** Hvert 30. sekund sender klienten en lettvekts ping (`Channel/GetAllConf`) til enheten for å forhindre at WiFi-strømsparingsmodus kobler fra
- **Eksponentiell backoff:** Ved kommunikasjonsfeil starter en venteperiode på 3 sekunder som dobles for hver påfølgende feil (3s -> 6s -> 12s -> 24s -> ...) opp til maks 60 sekunder. Tilbakestilles til 3s ved første vellykkede kommunikasjon
- **Auto-reboot:** Etter 5 sammenhengende enhetsfeil sendes en `Device/SysReboot`-kommando. Deretter venter systemet 30 sekunder for at enheten skal koble seg til igjen før normal drift gjenopptas
- Alle tre mekanismene virker sammen: ping oppdager problemer tidlig, backoff forhindrer overbelastning av en treg enhet, og reboot er siste utvei når ingenting annet fungerer

**Auto-lysstyrke (astronomisk):**
- Bruker `astral`-biblioteket for å beregne faktisk soloppgang, solnedgang og sivil skumring basert på bredde-/lengdegrad
- Dag (etter morgenskumring): 100% (begrenset til 90% av klienten)
- Natt (etter kveldsskumring): 20% -- lesbart uten å lyse opp rommet
- Følger sesongene automatisk: i desember dimmes det allerede kl. 15--16, i juni holder det seg lyst til kl. 22--23

---

## Bursdagsoverraskelse

Konfigurer bursdagsdatoer i `.env` med `BIRTHDAY_DATES` (kommaseparert MM-DD-format):

```bash
BIRTHDAY_DATES=01-01,06-15
```

På disse datoene får displayet en festlig touch:
- Klokketeksten blir **gyllen**
- Datoteksten blir **rosa**
- En liten **5x5-pikslers krone** dukker opp øverst i høyre hjørne
- **Glitrende piksler** i klokke/dato-sonen (deterministiske posisjoner -- ingen flimring mellom bilder)

---

## Lisens

Dette er et personlig hobbyprosjekt. Koden er tilgjengelig for inspirasjon og læring.
