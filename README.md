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
