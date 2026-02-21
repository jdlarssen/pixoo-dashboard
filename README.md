# Divoom Hub

> Alltid-pa LED-dashbord for Pixoo 64 -- klokke, bussavganger og vaer med et blikk.

[![Bygget med Claude Code](https://img.shields.io/badge/Bygget_med-Claude_Code-orange?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/code)

<!-- Bytt ut bildet nedenfor med et ekte foto av displayet ditt.
     Legg bildet i docs/display-photo.jpg (eller endre stien). -->
![Pixoo 64-dashbordet i aksjon](docs/display-photo.jpg)

Et personlig hjemmedashbord som kjorer pa en Divoom Pixoo 64 LED-skjerm. Med et raskt blikk pa displayet ser du hva klokka er, nar neste buss gar, og hvordan vaeret er -- uten a ta opp telefonen.

Prosjektet er bygget som et hobbyprosjekt for eget bruk. Displayet star pa en hylle og viser sanntidsdata dognets 24 timer: klokke med norsk dato, bussavganger fra to retninger med nedtelling i farger (gronn, gul, rod), vaermelding med animerte overlegg (regn, sno, sol, torden, taake), og en valgfri Discord-meldingsfunksjon for a sende korte beskjeder til skjermen.

Alt er skrevet i Python og snakker med Pixoo 64 over lokalnettverket. Vaerdata kommer fra MET Norway (yr.no-backend), bussdata fra Entur, og klokka formateres pa norsk med ae, oe og aa.

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
|  7   2.3mm                                                VAER  |  y 40-49
|  5/2          ~~~                                               |  y 50-58
|                ~~~                                              |  y 59-63
+----------------------------------------------------------------+
```

| Sone | Y-start | Y-slutt | Hoyde | Innhold |
|------|---------|---------|-------|---------|
| Klokke | 0 | 10 | 11 px | HH:MM i 24-timers format + vaerikon |
| Dato | 11 | 18 | 8 px | Norsk dato, f.eks. "tor 20. feb" |
| Skillelinje | 19 | 19 | 1 px | Tynn teal-strek |
| Buss | 20 | 38 | 19 px | To retninger med fargekodede nedtellinger |
| Skillelinje | 39 | 39 | 1 px | Tynn teal-strek |
| Vaer | 40 | 63 | 24 px | Temperatur, hoy/lav, nedbor, animasjon |

**Bussnedtelling i farger:**
- Gronn: > 10 min (god tid)
- Gul: 5--10 min (skynd deg)
- Rod: < 5 min (snart borte)
- Dimmet: < 2 min (bussen er i praksis borte)

---

## Forutsetninger

- **Python 3.10+**
- **Divoom Pixoo 64** pa samme lokalnettverk (LAN)
- Internettforbindelse for vaer- og buss-API-er

Avhengigheter (installeres automatisk):

| Pakke | Versjon | Formal |
|-------|---------|--------|
| pixoo | -- | Kommunikasjon med Pixoo 64 |
| Pillow | >= 12.1.0 | Bildebehandling og fontrendering |
| discord.py | >= 2.0 | Valgfri Discord-meldingsoverstyring |
| python-dotenv | >= 1.0 | Lasting av .env-konfigurasjon |

---

## Installasjon

```bash
git clone https://github.com/YOUR_USERNAME/divoom-hub.git
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

### Pakrevde variabler

| Variabel | Beskrivelse | Eksempel |
|----------|-------------|----------|
| `DIVOOM_IP` | IP-adressen til Pixoo 64 pa LAN | `192.168.1.100` |
| `BUS_QUAY_DIR1` | Entur quay-ID for retning 1 | `NSR:Quay:XXXXX` |
| `BUS_QUAY_DIR2` | Entur quay-ID for retning 2 | `NSR:Quay:XXXXX` |
| `WEATHER_LAT` | Breddegrad (desimalgrader) | `59.9139` |
| `WEATHER_LON` | Lengdegrad (desimalgrader) | `10.7522` |

Finn dine quay-ID-er pa [stoppested.entur.org](https://stoppested.entur.org) og koordinater pa [latlong.net](https://www.latlong.net).

### Valgfrie variabler

| Variabel | Beskrivelse | Standard |
|----------|-------------|----------|
| `ET_CLIENT_NAME` | Identifiserer appen mot Entur API | `pixoo-dashboard` |
| `WEATHER_USER_AGENT` | User-Agent for MET Norway API (pabudt) | `pixoo-dashboard/1.0` |
| `DISCORD_BOT_TOKEN` | Discord-bot-token for meldingsoverstyring | *(deaktivert)* |
| `DISCORD_CHANNEL_ID` | Discord-kanal-ID for meldinger | *(deaktivert)* |
| `BIRTHDAY_DATES` | Bursdagsdatoer for easter egg (MM-DD, kommaseparert) | *(ingen)* |

<details>
<summary>Komplett .env-eksempel</summary>

```bash
# === PAKREVD ===
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
# BIRTHDAY_DATES=01-01,06-15
```

</details>

---

## Bruk

```bash
# Standard kjoring (krever Pixoo 64 pa nettverket)
python src/main.py

# Med egendefinert IP-adresse
python src/main.py --ip 192.168.1.100

# Simulatormodus (ingen maskinvare -- apner Tkinter-vindu)
python src/main.py --simulated

# Debug-modus (lagrer hvert bilde til debug_frame.png)
python src/main.py --save-frame

# Test vaeranimasjon (kombineres gjerne med --simulated)
TEST_WEATHER=rain python src/main.py --simulated
```

Tilgjengelige vaertyper for `TEST_WEATHER`: `clear`, `rain`, `snow`, `fog`, `cloudy`, `sun`, `thunder`

---

## Kjore som tjeneste (macOS launchd)

Prosjektet inkluderer en ferdig `com.divoom-hub.dashboard.plist` for automatisk oppstart.

<details>
<summary>Steg-for-steg oppsett</summary>

**1. Rediger stier i plist-filen**

Apne `com.divoom-hub.dashboard.plist` og erstatt `/EDIT/PATH/TO/` med den faktiske stien til prosjektet. Oppdater ogsa IP-adressen til din Pixoo 64.

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

Dette prosjektet ble bygget fra bunnen av med [Claude Code](https://claude.ai/code) -- Anthropics CLI-verktoy for AI-assistert utvikling. Fra forste linje Python til siste piksel pa displayet har Claude vaert utviklingspartneren.

Hele prosessen fulgte en strukturert arbeidsflyt: kravdefinisjon, arkitekturplanlegging, implementering i faser, testing og verifisering -- alt drevet av samtaler med Claude. Prosjektet gikk fra ide til ferdig dashbord pa en enkelt dag.

Det er ikke et eksperiment i "la AI skrive all koden" -- det er et samarbeidsprosjekt der et menneske definerte hva som skulle bygges, tok designbeslutninger og validerte resultatene, mens Claude stod for implementeringen, feilsoking og testing.

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
│   ├── state.py          # DisplayState med dirty flag-monster
│   ├── weather_anim.py   # 8 animasjonstyper med dybdelag
│   └── weather_icons.py  # Pikselkunst-vaerikon (10x10 px)
└── providers/
    ├── bus.py            # Entur JourneyPlanner v3 (GraphQL)
    ├── clock.py          # Norsk tid- og datoformatering
    ├── discord_bot.py    # Discord-meldingsoverstyring (daemon-trad)
    └── weather.py        # MET Norway Locationforecast 2.0
```

### Dataflyt

```
main_loop()
  ├── fetch_bus_data()         → Entur GraphQL API (hvert 60. sekund)
  ├── fetch_weather_safe()     → MET Norway API (hvert 600. sekund)
  ├── weather_anim.tick()      → bg/fg RGBA-lag (~3 FPS)
  ├── DisplayState.from_now()  → dirty flag-sjekk
  ├── render_frame()           → 64x64 PIL-bilde
  └── client.push_frame()     → Pixoo 64 via HTTP
```

**Dirty flag-monsteret:** `DisplayState` er en dataklasse med likhetskontroll. Hovedloopen sammenligner forrige og navaerende tilstand -- bildet rendres kun pa nytt nar noe faktisk har endret seg (nytt minutt, nye bussdata, nytt vaer).

**To hastigheter:** Nar vaeranimasjon er aktiv kjorer loopen med 0.35s pause (~3 FPS). Nar det er stille vaer, sover den 1 sekund mellom hver sjekk.

---

## API-er

<details>
<summary>Entur JourneyPlanner v3 (bussdata)</summary>

**Endepunkt:** `https://api.entur.io/journey-planner/v3/graphql`

**Pabudt header:** `ET-Client-Name` -- identifiserer appen din mot Entur.

Appen sender et GraphQL-query som henter `estimatedCalls` for en gitt quay-ID. Hver avgang gir `expectedDepartureTime` (sanntid nar tilgjengelig), `aimedDepartureTime`, `realtime`-flagg, og destinasjonsinfo.

**Gotchas:**
- Kansellerte avganger finnes i svaret -- appen filtrerer dem bort og ber om ekstra avganger for a kompensere
- Tidsberegning: `expectedDepartureTime` er ISO 8601 med tidssone, konverteres til nedtellingsminutter med `datetime.fromisoformat()`
- Nedtelling klippes til minimum 0 (ingen negative verdier)

</details>

<details>
<summary>MET Norway Locationforecast 2.0 (vaerdata)</summary>

**Endepunkt:** `https://api.met.no/weatherapi/locationforecast/2.0/compact`

**Pabudt header:** `User-Agent` -- MET krever identifikasjon per bruksvilkar.

Appen bruker `If-Modified-Since`-caching: forste kall laster ned full respons, deretter sendes `Last-Modified`-verdien tilbake. MET returnerer `304 Not Modified` nar data er uendret, noe som sparer bandbredde og respekterer API-vilkarene. Cachen lagres pa moduldniva i Python.

**Svaret inneholder:**
- `timeseries` med vaerdata per tidspunkt
- Hvert tidspunkt har `instant` (navaerende), `next_1_hours` og `next_6_hours` prognoser
- `symbol_code` (f.eks. `clearsky_day`, `rain_night`) brukes for ikon- og animasjonsvalg

**Gotchas:**
- Hoy/lav-temperatur er ikke et eget felt -- appen skanner alle tidspunkter for dagens dato og finner maks/min
- `symbol_code` har suffikser (`_day`, `_night`, `_polartwilight`) som ma strippes for ikonoppslag
- API-et oppdateres omtrent hvert 10. minutt

</details>

---

## Discord-meldingsoverstyring

En valgfri Discord-bot lar deg sende korte meldinger til displayet. Boten kjorer i en bakgrunnstrad (daemon) og er helt uavhengig av hovedloopen.

**Oppsett:**
1. Opprett en Discord-bot pa [discord.com/developers](https://discord.com/developers/applications)
2. Aktiver "Message Content Intent"
3. Inviter boten til en server og en kanal
4. Legg til `DISCORD_BOT_TOKEN` og `DISCORD_CHANNEL_ID` i `.env`

**Bruk:**
- Skriv en melding i kanalen -- den vises i vaersonen pa displayet
- Skriv `clear`, `cls` eller `reset` for a fjerne meldingen
- Boten reagerer med et avkrysningsmerke for a bekrefte mottak

Meldingen vises i nedre del av vaersonen (under temperatur og hoy/lav). Nar en melding er aktiv, skjules nedborsindikatatoren for a gi plass.

Hvis `DISCORD_BOT_TOKEN` eller `DISCORD_CHANNEL_ID` ikke er satt, starter boten rett og slett ikke -- ingen feilmelding, ingen pavirkning pa dashbordet.

---

## Vaeranimasjonar

Vaersonen (24 piksler hoy) har animerte overlegg som gir liv til displayet. Systemet bruker et 3D-dybdeeffekt med to lag:

- **Bakgrunnslag** (bak tekst): fjerne, dimmere partikler
- **Forgrunnslag** (foran tekst): naere, lysere partikler

Hvert bilde rendres ved a legge bakgrunnslaget under teksten og forgrunnslaget over -- dette skaper en illusjon av dybde pa en flat 64x64-skjerm.

<details>
<summary>De 8 animasjonstypene</summary>

| Type | Beskrivelse |
|------|-------------|
| **Regn** | Bla draper i to dybder -- fjerne draper er dimmere og kortere, naere er lysere med 3px streker |
| **Sno** | Krystaller i + form (naere, lyse) og enkeltpiksler (fjerne, dimme) som driver sakte |
| **Sol** | Diagonale gylne solstraler som faller nedover i to hastigheter |
| **Skyer** | Gra-hvite skyellipser som driver sakte gjennom sonen |
| **Torden** | Regn + lyn hvert ~4. sekund med 3-bilders syklus (blink, etterglod, fade) |
| **Taake** | Skyblober som driver gjennom hoyre side av sonen |
| **Delvis skyet** | Samme som sol |
| **Sludd** | Samme som regn |

</details>

Animasjonene kjorer med ~3 FPS (0.35s mellom hvert bilde). Alpha-verdier er tunet for LED-maskinvarens synlighet (65--180-omradet).

---

## Norske tegn og fonter

Displayet bruker BDF-bitmap-fonter i tre storrelser:

| Font | Storrelse | Brukes til |
|------|-----------|-----------|
| 4x6 | 4x6 px | Hoy/lav-temperatur, nedbor, meldinger |
| 5x8 | 5x8 px | Klokke, dato, bussnedtellinger |
| 7x13 | 7x13 px | Tilgjengelig, ikke i bruk |

Fontene lastes fra `assets/fonts/`-mappen. BDF-filene konverteres automatisk til PIL-format (`.pil` + `.pbm`) ved forste kjoring -- disse genererte filene er i `.gitignore`.

Norske spesialtegn (ae, oe, aa) finnes i BDF-fontene og brukes i dagsnavn: **lordag** og **sondag** inneholder oe. Klokkeleverandoren (`clock.py`) bruker egne norske ordbokoppslag for dag- og manedsnavn istedenfor systemets locale -- dette unnga avhengighet pa installert sprakstotte.

---

## Feilhandtering

Dashbordet er designet for a kjore dognkontinuerlig uten tilsyn. Flere lag med feilhandtering holder det stabilt:

**Staleness-sporing (foreldet data):**

| Datakilde | Stale (aldrende) | For gammel (vises ikke) |
|-----------|-------------------|------------------------|
| Buss | > 3 min | > 10 min |
| Vaer | > 30 min | > 1 time |

- Nar data er *stale* men brukbar: vises med en oransje prikk overst i hoyre hjorne av sonen
- Nar data er *for gammel*: erstattes med `--` plassholdere
- Ved API-feil: siste vellykkede data beholdes og vises videre

**Enhetstilkobling:**
- `pixoo`-bibliotekets `refresh_connection_automatically` forhindrer at tilkoblingen laser seg etter ~300 push-operasjoner
- Rate limiting: minimum 0.3 sekunder mellom hvert bilde (forhindrer tapte frames ved timing-jitter)
- Lysstyrke begrenset til 90% (`MAX_BRIGHTNESS`) -- full lysstyrke kan krasje enheten

**Auto-lysstyrke:**
- Dag (06:00--21:00): 100% (begrenset til 90% av klienten)
- Natt (21:00--06:00): 20% -- lesbart uten a lyse opp rommet

---

## Bursdagsoverraskelse

Konfigurer bursdagsdatoer i `.env` med `BIRTHDAY_DATES` (kommaseparert MM-DD-format):

```bash
BIRTHDAY_DATES=01-01,06-15
```

Pa disse datoene far displayet en festlig touch:
- Klokketeksten blir **gyllen**
- Datoteksten blir **rosa**
- En liten **5x5-pikslers krone** dukker opp overst i hoyre hjorne
- **Glitrende piksler** i klokke/dato-sonen (deterministiske posisjoner -- ingen flimring mellom bilder)

---

## Lisens

Dette er et personlig hobbyprosjekt. Koden er tilgjengelig for inspirasjon og laring.
