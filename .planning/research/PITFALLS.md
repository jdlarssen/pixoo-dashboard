# Pitfalls Research

**Domain:** v1.1 Documentation & Polish -- Norwegian README, weather animation color fix, Claude Code attribution
**Researched:** 2026-02-21
**Confidence:** HIGH (pitfalls derive from codebase inspection, existing debug history, and established open-source documentation patterns)

## Critical Pitfalls

### Pitfall 1: Weather Color Fix Breaks the 3D Depth Compositing System

**What goes wrong:**
Changing particle colors in `weather_anim.py` without understanding the two-layer compositing pipeline produces colors that look correct in unit tests (isolated RGBA images) but wrong on the actual display. The renderer composites bg_layer BEHIND text and fg_layer IN FRONT of text via `_composite_layer()` in `renderer.py:121-125`. If new colors are too vivid in the fg_layer, they obscure temperature and rain text. If new bg_layer colors are too dim, they remain invisible after alpha compositing over the black background.

**Why it happens:**
The compositing is a 3-step pipeline: (1) crop existing RGB region, (2) convert to RGBA, (3) `Image.alpha_composite()` the animation layer on top. The final pixel color depends on the interaction of the animation's RGBA value with the existing background content. A color that looks great in isolation (e.g., bright blue rain at alpha 200) will wash out the warm yellow temperature text `(255, 200, 50)` when composited in the fg_layer, making the temperature unreadable. This was already the root cause of the v1.0 debug session (`weather-animation-too-subtle.md`) where double-alpha application made everything invisible.

**How to avoid:**
- Test color changes on the physical Pixoo 64 hardware, not just in unit tests or on-screen PNG previews. LED matrix color rendering differs significantly from LCD/OLED screens.
- Maintain the existing alpha ranges that were empirically validated: bg_layer 40-100, fg_layer 90-200. Do not exceed fg_layer alpha 200 or text becomes unreadable.
- Change colors (RGB channels) independently from brightness (alpha channel). The current alpha values in `weather_anim.py` were tuned specifically for LED visibility after the v1.0 debug session.
- Test each weather animation type individually: rain, snow, cloud, sun, thunder, fog. Each has different particle density and coverage patterns.

**Warning signs:**
- Temperature text becomes hard to read during rain/snow animations (fg_layer too opaque or color too close to text color).
- Rain and snow still look the same color despite having different RGB values (alpha too low, LED minimum brightness threshold not met).
- Existing tests in `test_weather_anim.py` pass but the display looks wrong (tests only check alpha thresholds, not perceptual color contrast).

**Phase to address:**
Weather color fix phase. Must include physical hardware testing as acceptance criteria, not just unit test assertions.

---

### Pitfall 2: Rain Text Color Collides With Rain Particle Color After Fix

**What goes wrong:**
The existing bug is that rain particles and rain text ("1.2mm") are both grey/indistinguishable. The natural fix is to make rain particles blue. But the rain indicator text `COLOR_WEATHER_RAIN` in `layout.py:61` is already `(50, 180, 255)` -- vivid blue. If rain particles become blue too (the todo suggests blue-tinted rain), the text-vs-particle distinction problem recurs with a different color. You solve "both are grey" and create "both are blue."

**Why it happens:**
The color palette was designed before the animation system had vivid particle colors. The rain text was given a blue color because rain = blue is intuitive for text. But animation particles also need to read as rain = blue. When both are blue, the composited result blends them together, especially since the fg_layer particles pass IN FRONT of the text.

**How to avoid:**
- Choose particle colors and text colors as a coordinated palette, not independently. Map out all colors that appear simultaneously in the weather zone: `COLOR_WEATHER_TEMP` (yellow), `COLOR_WEATHER_HILO` (teal), `COLOR_WEATHER_RAIN` (blue), and the animation particle color.
- Use the hue wheel: temperature text is warm yellow (hue ~45), rain text is blue (hue ~210), so rain particles should be a DIFFERENT blue (darker/more saturated, e.g., `(30, 60, 200)`) or the rain text should shift to cyan/white to contrast with blue particles.
- The fg_layer near-drops are the primary conflict since they render ON TOP of text. Their color must contrast with all text colors in the zone.

**Warning signs:**
- Rain text "disappears" during rain animation because it is the same hue as the particles passing over it.
- User cannot tell if the display is showing "1.2mm" or just animated rain pixels in the same area.

**Phase to address:**
Weather color fix phase. The color palette for the entire weather zone must be redesigned as a unit, not just the particle colors in isolation.

---

### Pitfall 3: Norwegian README Written in English-Thinking Patterns

**What goes wrong:**
The README is written in grammatically correct Norwegian but reads as a direct translation from English, making it feel unnatural to native speakers. Technical documentation in Norwegian has specific conventions that differ from English: sentence structure, terminology choices (e.g., "kjor" vs "run", "oppsett" vs "setup"), and section naming conventions.

**Why it happens:**
AI-assisted writing (and non-native speakers) tend to produce "English with Norwegian words" rather than idiomatic Norwegian. Common mistakes: using English loan-word ordering ("Pixoo 64 dashbord" instead of the more natural "dashbord for Pixoo 64"), translating idioms literally, using overly formal bokmaal when casual would be more natural for a hobby project, and inconsistent treatment of English technical terms.

**How to avoid:**
- Keep English technical terms in English where Norwegian developers would naturally use them: "API", "README", "pull request", "commit", "fork", "dashboard", "LED", "pip", "Python". Do NOT translate these.
- Use natural Norwegian for descriptive text: "Slik setter du det opp" not "Hvordan a sette opp".
- Section headers should follow Norwegian README conventions: "Kom i gang" (Getting Started), "Installasjon" (Installation), "Bruk" (Usage), "Bidra" (Contributing).
- Review against existing Norwegian open-source READMEs for tone and convention (e.g., nav/nav, NRK open-source projects).
- The project already uses Norwegian date strings with proper encoding (verified in v1.0: `loerdag`, `februar`, etc.), so the conventions for ae/oe/aa are established.

**Warning signs:**
- README sounds stilted or overly formal compared to the project's casual, personal nature.
- Technical terms are inconsistently translated (mixing "installasjon" with "install" randomly).
- Section structure follows English conventions that do not map to Norwegian reader expectations.

**Phase to address:**
README phase. Should include a review pass specifically for natural Norwegian language flow.

---

### Pitfall 4: README Documents .env Secrets or Hardcoded Personal Details

**What goes wrong:**
The README includes setup instructions that accidentally expose real configuration values: the actual Ladeveien bus stop IDs, the user's home coordinates, Discord bot tokens, or the real device IP. These end up committed in the README and indexed by search engines. The `.env` file is gitignored, but example values in the README are not.

**Why it happens:**
When writing setup documentation, it is natural to copy-paste from the working `.env` file as examples. The project's `.env.example` already has safe placeholder values, but the README might be written using the real config as reference. The real bus stop IDs (`NSR:Quay:73154`, `NSR:Quay:73152`) are already in `PROJECT.md` (which is in `.planning/`, typically not public), but copying them to the README exposes the user's specific location.

**How to avoid:**
- Use explicitly fake example values in the README: `DIVOOM_IP=192.168.1.XXX`, `BUS_QUAY_DIR1=NSR:Quay:XXXXX`. Reference `.env.example` for the template.
- Do not include the user's real latitude/longitude. Use Oslo city center or a generic Norwegian location as the example.
- For Discord bot setup, reference Discord's official documentation rather than including token formats.
- Grep the README draft for any string that appears in the actual `.env` file before committing.
- The `.env.example` file already has safe placeholders -- the README should point to it rather than duplicating configuration examples.

**Warning signs:**
- README contains coordinates that resolve to a specific residential address.
- Bus stop IDs in the README match the user's actual stops.
- Discord bot token or channel ID appears anywhere in tracked files.

**Phase to address:**
README phase. Final review must include a secrets scan of the README content.

---

### Pitfall 5: Claude Code Attribution Positioned as Apology Rather Than Transparency

**What goes wrong:**
The "Built with Claude Code" section reads as a disclaimer or apology ("this code was AI-generated, so...") rather than genuine transparency about the development process. This either undermines confidence in the code quality or comes across as performative. Alternatively, it overstates AI contribution by implying the AI designed the architecture when the human made all product decisions.

**Why it happens:**
There is no established convention for AI attribution in open-source projects (as of 2026). Most projects either hide AI usage entirely or add a generic badge with no context. The honest middle ground -- describing how AI was used as a tool in a human-directed process -- requires careful framing.

**How to avoid:**
- Frame it as a development methodology note, not a code quality disclaimer. Example: "Utviklet med Claude Code som AI-verktoy. Alle produktbeslutninger, arkitektur og UX-valg er gjort av utvikleren." (Developed with Claude Code as an AI tool. All product decisions, architecture, and UX choices were made by the developer.)
- Include the badge near the top for visibility, but put the detailed description in a "Utvikling" (Development) section, not in the main project description.
- Be specific about what AI helped with (code implementation, debugging, test writing) and what was human-driven (feature selection, layout design, color choices, API selection).
- Do not frame it as a warning. The project has 96 passing tests and was validated through extensive UAT on real hardware -- the quality speaks for itself.

**Warning signs:**
- The attribution section contains phrases like "may contain errors" or "use at your own risk" that would not appear without AI involvement.
- The badge is hidden at the bottom of the README where no one sees it (defeating the transparency purpose).
- Attribution claims AI did things the human actually decided (architecture, product decisions).

**Phase to address:**
README phase. The attribution section should be drafted alongside the main README, not bolted on afterward.

---

### Pitfall 6: Changing Weather Colors Without Updating Tests

**What goes wrong:**
The existing `test_weather_anim.py` tests check alpha thresholds (e.g., "rain max alpha >= 100") but do not verify specific colors. After changing particle colors from grey to blue/white, the tests still pass because they only check alpha values. This means a future change could regress the colors back to grey (or to conflicting colors) without any test catching it.

**Why it happens:**
The original tests were written during the v1.0 visibility fix to prevent the "invisible animation" regression. They solved the problem at hand (alpha too low) but were not designed to prevent color regression. Color testing on LED hardware is inherently hard -- RGB values on a screen look different on LEDs -- so developers skip it.

**How to avoid:**
- Add color-identity tests: verify rain particles contain blue channel values > red/green (asserting they are blue, not grey). Verify snow particles have roughly equal high RGB values (asserting white, not grey).
- Add a contrast test: verify that the dominant color of rain particles differs from `COLOR_WEATHER_RAIN` text color by a minimum perceptual distance (e.g., hue difference > 30 degrees or luminance difference > 40).
- The tests do not need to verify exact RGB values (which would be fragile), but should verify color IDENTITY (rain = blue-ish, snow = white-ish, sun = yellow-ish).

**Warning signs:**
- All existing tests pass after the color change (meaning the tests did not actually validate color, only alpha).
- No test would catch reverting rain color from blue back to grey.

**Phase to address:**
Weather color fix phase. New color-identity tests should be part of the same change as the color fix.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| README in English only | Faster to write, wider audience | Project is Norwegian-context-specific (Trondheim buses, Norwegian dates) -- English README misrepresents the audience | Never for this project -- Norwegian is the user's preference and the project's context |
| Hardcoded color values in animation classes | Quick to change, no abstraction overhead | Color changes require editing 6 animation classes + layout.py; no central palette | Acceptable for v1.1 -- the project has 6 animation types and is unlikely to grow. A color constants module would be over-engineering |
| AI badge without explanation | Minimal effort, technically transparent | Leaves interpretation to the reader, who may assume more or less AI involvement than reality | Never -- the whole point is meaningful transparency |
| Skipping hardware testing for color changes | Faster iteration, CI-testable | Colors that pass tests may be invisible/ugly on the actual LED matrix | Never for display changes -- LED rendering is fundamentally different from screen rendering |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PIL alpha compositing | Testing composited colors by viewing PNG on a monitor | View on physical Pixoo 64 LED matrix -- LEDs have minimum brightness thresholds, non-linear brightness curves, and different color gamut than LCD/OLED |
| GitHub README rendering | Using Norwegian characters without specifying UTF-8 | GitHub renders Markdown as UTF-8 by default. No explicit encoding needed, but verify ae/oe/aa render correctly in the GitHub preview. The `.md` file itself must be saved as UTF-8 |
| GitHub badges | Using badge service URLs that break | Use shields.io static badges or inline markdown images. Avoid custom badge services that may go offline |
| Weather animation + text compositing | Changing fg_layer colors without checking text readability | After any color change, verify that temperature text (yellow), high/low text (teal), and rain text (blue) are all still legible through the animation overlay |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Not applicable for v1.1 | This milestone adds a README and changes color constants -- no performance-impacting changes | N/A | N/A |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Including real GPS coordinates in README | Exposes user's home address to anyone who reads the repo | Use generic example coordinates (Oslo city center: 59.9139, 10.7522 -- already the default in `.env.example`) |
| Including real bus stop IDs in README | Narrows location to a specific street intersection | Use placeholder `NSR:Quay:XXXXX` with instructions to find your own at stoppested.entur.org |
| Including Discord bot token patterns | Reduces token entropy if partial token is exposed | Never include real or realistic-looking tokens. Use `your-bot-token-here` exactly |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Rain particles same blue as rain text | User still cannot distinguish particles from text data -- original bug returns with a different color | Ensure minimum 30-degree hue separation between particle color and any text color in the weather zone |
| Snow particles too white on black background | Snow overpowers the display and makes text hard to read | Keep snow slightly tinted (cool blue-white) and use moderate alpha (120-180) so text shows through |
| All animations same brightness | User cannot distinguish weather conditions at a glance -- "something is moving" but unclear what | Each animation type should have a distinct visual character: rain=vertical streaks, snow=gentle drift, sun=diagonal rays. Color is secondary to motion pattern |

## "Looks Done But Isn't" Checklist

- [ ] **Norwegian README:** Renders correctly on GitHub (ae/oe/aa display properly) -- verify by viewing the raw GitHub page, not just the local Markdown preview
- [ ] **Norwegian README:** All code examples actually work when copy-pasted -- verify `pip install`, `python -m src.main`, config steps
- [ ] **Norwegian README:** No real personal data in examples -- grep for actual `.env` values, GPS coordinates, Discord tokens
- [ ] **Norwegian README:** Links to external resources (Entur, MET Norway, shields.io) are not broken -- click-test each link
- [ ] **Rain color fix:** Rain particles are visually blue on the physical LED display, not just in test assertions -- view at 2 meters
- [ ] **Snow color fix:** Snow particles are visually distinct from rain particles on the LED display -- view both animation types back-to-back
- [ ] **Color fix:** Temperature text remains readable during all weather animations -- test each of the 8 weather groups
- [ ] **Color fix:** Rain text ("1.2mm") remains readable during rain animation -- the fg_layer passes over this text
- [ ] **Color fix:** Tests exist that would catch a color regression (not just alpha regression)
- [ ] **Claude badge:** Badge image renders on GitHub (not a broken image link)
- [ ] **Claude attribution:** Attribution is factually accurate about what was AI-assisted vs human-decided

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Color fix breaks text readability | LOW | Revert the color values in `weather_anim.py` -- all changes are constant values. No architectural impact |
| README exposes personal data | MEDIUM | Remove from README and commit, but the data remains in git history. May need `git filter-branch` or BFG Repo Cleaner to purge from history |
| Norwegian language quality is poor | LOW | Revise the text. No code changes needed. Can be iterated without affecting functionality |
| Badge link breaks | LOW | Replace badge URL or switch to static inline image. One-line change in README |
| Color regression after future changes | LOW | If color-identity tests were added, regression is caught automatically. If not, manual hardware testing is needed |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Compositing color interaction | Weather color fix | View all 8 weather animations on physical Pixoo 64 with temperature text visible |
| Rain text/particle color collision | Weather color fix | Compare rain animation with rain indicator text side-by-side on display |
| Norwegian language quality | README writing | Native speaker review pass or comparison against established Norwegian OSS READMEs |
| Secrets in README | README writing | Diff README against `.env` file; grep for coordinate numbers, quay IDs, tokens |
| AI attribution framing | README writing | Read attribution section in isolation -- does it sound like a disclaimer or a methodology note? |
| Missing color regression tests | Weather color fix | Verify test suite would catch revert of rain color from blue to grey |

## Sources

- Project codebase inspection: `src/display/weather_anim.py`, `src/display/renderer.py`, `src/display/layout.py` -- HIGH confidence: direct code reading
- Debug session: `.planning/debug/weather-animation-too-subtle.md` -- HIGH confidence: documented root cause analysis with pixel-level calculations
- Todo: `.planning/todos/done/2026-02-20-weather-animation-and-rain-text-colors-indistinguishable.md` -- HIGH confidence: user-reported bug with specific symptoms
- Existing test suite: `tests/test_weather_anim.py` -- HIGH confidence: shows what is and is not tested
- `.env.example` and `.gitignore` -- HIGH confidence: shows what is protected and what is exposed
- Norwegian open-source conventions -- MEDIUM confidence: based on patterns observed in NRK and NAV GitHub organizations

---
*Pitfalls research for: v1.1 Documentation & Polish (Norwegian README, weather color fix, Claude Code attribution)*
*Researched: 2026-02-21*
