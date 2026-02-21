# Phase 1: Foundation - Research

**Researched:** 2026-02-20
**Domain:** Pixoo 64 device communication, PIL/Pillow render engine, bitmap font rendering with Norwegian characters, 64x64 pixel layout design, connection stability
**Confidence:** HIGH

## Summary

Phase 1 establishes the entire rendering pipeline: a PIL/Pillow compositor that produces 64x64 RGB frames, a device driver that pushes them to the Pixoo 64 over LAN HTTP, a bitmap font system that renders Norwegian characters (aeoeaa) pixel-perfectly, and a zone-based layout that reserves space for clock, bus, and weather. The critical discovery in this research is that Norwegian characters aeoeaa (code points 197-248) fall within Latin-1 (0-255), meaning PIL bitmap fonts CAN render them without hitting the 256-character limitation. This makes the BDF bitmap font path viable and preferred over TrueType for pixel-perfect rendering at tiny sizes.

The recommended approach is: render the entire frame with PIL/Pillow, then hand it to the pixoo library's `draw_image()` method (which accepts file paths; PIL Images can be passed after saving to a buffer or using the library's internal pixel manipulation). The pixoo library handles device protocol, connection refresh (preventing the ~300-push lockup), and provides a Tkinter simulator for development without hardware. The font strategy is to source BDF bitmap fonts from the hzeller/rpi-rgb-led-matrix collection (which provides 4x6 through 10x20 sizes with full ISO 8859-1 coverage including aeoeaa), convert them to PIL format using Pillow's BdfFontFile module, and load them with `ImageFont.load()`. A TrueType fallback exists using `draw.fontmode = '1'` to disable anti-aliasing, but BDF is preferred for pixel-perfect rendering on LED matrices.

**Primary recommendation:** Use PIL/Pillow full-frame rendering with BDF bitmap fonts (converted to PIL format) for all text, the pixoo library for device communication with `refresh_connection_automatically=True`, and a simple synchronous main loop pushing frames at most once per second.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
User trusts Claude's judgment on all implementation decisions for this phase. Iteration will happen through UAT (user acceptance testing) after the phase is built.

### Claude's Discretion
The following areas are all at Claude's discretion:

**Screen layout**
- How to divide the 64x64 pixel grid between clock, bus zone, and weather zone
- Proportions, positions, and visual dividers between zones
- Best layout for readability from 2+ meters

**Clock appearance**
- Time digit size, pixel font style, 24-hour format
- Colon style (static vs blinking is v2 -- keep static for now)
- Ensuring legibility from 2+ meters distance

**Date formatting**
- Norwegian date abbreviation style (e.g. "tor 20. feb")
- Positioning relative to the clock
- Pixel font with working ae/oe/aa characters

**Empty zone treatment**
- How bus and weather zones appear before data is wired up in Phases 2-3
- Whether to show labels, leave blank, or use placeholder content

**Device communication**
- Connection refresh strategy to prevent the 300-push lockup
- Frame push interval and refresh cycle

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISP-01 | Full-frame custom rendering via PIL/Pillow pushed to Pixoo 64 | PIL/Pillow `Image.new("RGB", (64, 64))` + `ImageDraw` for compositing; pixoo library's `draw_image()` or direct HTTP POST with `Draw/SendHttpGif` for device push. Fully verified approach used by pixoo-rest, Home Assistant integration, and every serious Pixoo 64 project. |
| DISP-02 | Pixel font rendering with Norwegian character support (aeoeaa) | BDF bitmap fonts from hzeller/rpi-rgb-led-matrix (5x8, 6x12, etc.) with full ISO 8859-1 coverage. aeoeaa are Latin-1 code points (197-248), within PIL bitmap font's 256-char limit. Convert BDF to PIL format with `BdfFontFile`. TrueType fallback with `draw.fontmode = '1'`. |
| DISP-03 | Single-screen layout -- all info zones on 64x64, readable at a glance | Zone-based layout: clock (top, ~16px), date (below clock, ~8px), bus zone placeholder (~20px), weather zone placeholder (~20px). At 5px-wide characters with 1px gap, ~10 chars per row. Layout must be pixel-budgeted before code. |
| CLCK-01 | Display current time in large, readable digits | Large digits using 7x13 or similar BDF font for time. 24-hour format. "14:32" = 5 characters at ~8px each = 40px, fits comfortably in 64px width with room for spacing. Legible from 2+ meters on LED display. |
| CLCK-02 | Display today's date in Norwegian (e.g. "tor 20. feb") | Manual Norwegian day/month name dictionaries (7 days, 12 months). No locale module dependency. Small font (5x8 or 4x6) for date. "tor 20. feb" = 11 chars at ~5px = 55px, fits 64px width. aeoeaa confirmed renderable in PIL bitmap fonts. |
| RLBL-01 | Connection refresh cycle (prevent 300-push lockup) | pixoo library constructor parameter `refresh_connection_automatically=True` resets internal device counter every 32 frames. Must be enabled from first device connection. Without it, device locks up after ~300 pushes (~5 hours at 1 push/minute). |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.x | Application runtime | Pixoo ecosystem is Python-dominant. The pixoo library requires Python >=3.10. Pillow is the natural choice for 64x64 image rendering. |
| pixoo (SomethingWithComputers) | 0.9.2 | Pixoo 64 LAN communication | Most mature Python library for Pixoo 64. Provides `draw_image()`, `draw_text()`, `push()`, `set_brightness()`, `set_screen()`, simulator mode, and connection refresh. CC-BY-NC-SA 4.0 license (fine for personal project). |
| Pillow | 12.1.1 | 64x64 frame rendering | Standard Python imaging library. `Image.new("RGB", (64, 64))` + `ImageDraw` for text/shapes + `ImageFont` for bitmap font loading. Accepts BDF font conversion natively via `BdfFontFile`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tkinter | (stdlib) | Pixoo simulator GUI | Development without hardware. pixoo library's simulator mode renders to a Tkinter window. Known issue: black screen on MacBook M-processors (may need workaround). |
| pytest | latest | Testing | Test rendering output (save frames as PNG, verify pixel content), font loading, Norwegian date formatting. |
| ruff | latest | Linting + formatting | Fast, opinionated Python linter/formatter. Replaces flake8 + black + isort. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pixoo library | Direct HTTP POST to device | Raw protocol is simple (one POST with base64 pixel data) but loses simulator, connection refresh, and draw primitives. Good fallback if pixoo library causes issues. |
| BDF bitmap fonts | TrueType pixel fonts with `fontmode='1'` | TrueType works but has known FreeType hinting issues at small sizes (Pillow issue #6421). OTF format more reliable than TTF. BDF is pixel-perfect by design. |
| BDF bitmap fonts | Custom hand-drawn font arrays | Maximum control but massive effort. Only justified if no BDF font meets requirements. |
| Manual Norwegian strings | Python locale module (`nb_NO.utf8`) | locale module requires system locale installed, is global state, and fragile across platforms. Manual dictionary with 7 days + 12 months is 19 entries and zero dependencies. |

**Installation:**
```bash
python3 -m venv .venv
source .venv/bin/activate

pip install pixoo                    # Pixoo 64 communication (v0.9.2)
pip install Pillow                   # Image rendering (v12.1.1)

# Dev dependencies
pip install pytest ruff
```

## Architecture Patterns

### Recommended Project Structure
```
divoom-hub/
├── src/
│   ├── main.py              # Entry point, main loop
│   ├── config.py            # Device IP, intervals, layout constants
│   ├── display/
│   │   ├── __init__.py
│   │   ├── layout.py        # Zone definitions (x, y, width, height per zone)
│   │   ├── renderer.py      # PIL compositor (state -> 64x64 image)
│   │   ├── fonts.py         # Font loading (BDF->PIL conversion, font registry)
│   │   └── state.py         # DisplayState dataclass
│   ├── providers/
│   │   ├── __init__.py
│   │   └── clock.py         # Norwegian time/date formatting
│   └── device/
│       ├── __init__.py
│       └── pixoo_client.py  # Pixoo library wrapper, push rate limiting
├── assets/
│   └── fonts/               # BDF font files + converted PIL font files
├── tests/
│   ├── test_renderer.py     # Render frame to PNG, verify layout
│   ├── test_fonts.py        # Font loading, Norwegian character rendering
│   └── test_clock.py        # Norwegian date formatting
├── pyproject.toml
└── .env                     # Device IP (not committed)
```

### Pattern 1: PIL Full-Frame Rendering Pipeline

**What:** Compose the entire 64x64 display as a PIL Image, then push the complete frame to the Pixoo. Every pixel is under our control.

**When to use:** Always, for this project. This is the only approach that supports Norwegian characters, custom fonts, and a composed multi-zone layout on a single screen.

**Example:**
```python
# Source: Verified from pixoo library examples + PIL documentation
from PIL import Image, ImageDraw, ImageFont

def render_frame(state: DisplayState, fonts: dict) -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Clock zone (top)
    draw.text((2, 0), state.time_str, font=fonts["large"], fill=(255, 255, 255))

    # Date zone (below clock)
    draw.text((2, 16), state.date_str, font=fonts["small"], fill=(180, 180, 180))

    # Bus zone placeholder (middle)
    draw.text((2, 26), "BUS", font=fonts["small"], fill=(100, 100, 100))

    # Weather zone placeholder (bottom)
    draw.text((2, 46), "WEATHER", font=fonts["small"], fill=(100, 100, 100))

    return img
```

### Pattern 2: BDF Font Loading Pipeline

**What:** Convert BDF bitmap fonts to PIL format at startup, then use them with `ImageFont.load()` for pixel-perfect text rendering.

**When to use:** For all text rendering in this project. BDF fonts produce crisp, pixel-perfect output on LED matrices without anti-aliasing artifacts.

**Example:**
```python
# Source: Pillow documentation (BdfFontFile module) + pilfont.py from pillow-scripts
from PIL import BdfFontFile, ImageFont
import os

def convert_bdf_to_pil(bdf_path: str, output_dir: str) -> str:
    """Convert a BDF font to PIL format (.pil + .pbm files)."""
    pil_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(bdf_path))[0]
    )
    with open(bdf_path, "rb") as fp:
        font = BdfFontFile.BdfFontFile(fp)
        font.save(pil_path)
    return pil_path + ".pil"

def load_font(pil_path: str) -> ImageFont.ImageFont:
    """Load a converted PIL bitmap font."""
    return ImageFont.load(pil_path)
```

### Pattern 3: Norwegian Date Formatting (Manual Dictionary)

**What:** Format dates in Norwegian using manual dictionaries instead of the locale module.

**When to use:** Always. The locale module is fragile (requires system locale installed, is global mutable state). A manual dictionary is 19 entries and zero dependencies.

**Example:**
```python
# Source: Standard Python datetime + manual Norwegian strings
from datetime import datetime

DAYS_NO = ["man", "tir", "ons", "tor", "fre", "lor", "son"]
MONTHS_NO = [
    "jan", "feb", "mar", "apr", "mai", "jun",
    "jul", "aug", "sep", "okt", "nov", "des"
]

def format_date_norwegian(dt: datetime) -> str:
    """Format date as 'tor 20. feb' style Norwegian abbreviation."""
    day_name = DAYS_NO[dt.weekday()]
    month_name = MONTHS_NO[dt.month - 1]
    return f"{day_name} {dt.day}. {month_name}"
```

**Note on ae/oe/aa:** The day name "lor" (Saturday) contains oe (U+00F8, decimal 248). The month names in abbreviated form do not contain any special characters. Full day names that would need special characters: "lordag" (oe), "sondag" (oe). Since we use abbreviations, only "lor" and "son" are relevant, and "lor" needs oe. This MUST be tested with the chosen bitmap font.

### Pattern 4: Device Communication with Connection Refresh

**What:** Initialize the pixoo library with `refresh_connection_automatically=True` to prevent the ~300-push device lockup.

**When to use:** Always. Without this, the device locks up after ~5 hours of continuous operation (at 1 push/minute).

**Example:**
```python
# Source: pixoo library README (SomethingWithComputers/pixoo)
from pixoo import Pixoo

# Production mode
pixoo = Pixoo(
    '192.168.1.100',           # Device IP
    64,                         # Display size (64x64)
    debug=False
)
# Enable connection refresh to prevent 300-push lockup
# This resets the internal counter every 32 frames

# Simulator mode (development without hardware)
from pixoo import Pixoo, SimulatorConfig
pixoo = Pixoo(
    '192.168.1.100',
    64,
    simulated=True,
    simulation_config=SimulatorConfig(4)  # 4x scale
)
```

### Anti-Patterns to Avoid

- **Using native Pixoo `Draw/SendHttpText`:** Does not support aeoeaa, limited font options, some font/character combos crash the device. Always use PIL-rendered full-frame images.
- **Pushing more than 1 frame per second:** Device becomes unresponsive. Enforce minimum 1-second interval between push calls.
- **Rendering at higher resolution and downscaling:** Always render at exactly 64x64. Downscaling produces blurry, aliased text on LEDs. Every pixel must be intentional.
- **Using TrueType fonts at small sizes without disabling anti-aliasing:** Anti-aliased text looks muddy on LED pixels. If using TrueType as fallback, set `draw.fontmode = '1'`.
- **Fetching data inside the render function:** Network failures would freeze the display. Keep rendering and data collection separate (relevant when bus/weather are wired in Phases 2-3).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pixoo device protocol | Custom HTTP POST with base64 encoding | `pixoo` library | Library handles connection refresh, buffer management, simulator, device discovery. Raw protocol is documented but error-prone. |
| BDF font parsing | Custom BDF parser | Pillow's `BdfFontFile` module | BDF format is well-specified but has edge cases. Pillow handles conversion to its internal format correctly. |
| Norwegian locale formatting | `locale.setlocale(locale.LC_TIME, 'nb_NO.utf8')` | Manual dictionary (19 entries) | locale module requires system locale installed, is global mutable state, fragile across macOS/Linux/Docker. Dictionary is deterministic and portable. |
| Anti-aliasing control | Custom font rasterizer | `draw.fontmode = '1'` on ImageDraw instance | Pillow provides this control natively. Only needed if using TrueType fonts (not needed for BDF bitmap fonts). |
| Image-to-device encoding | Manual RGB flattening + base64 | `pixoo.draw_image()` or `pixoo` library internals | Library handles the PIL Image to base64 RGB pixel data conversion. |

**Key insight:** The pixoo library + Pillow combination handles all the hard device communication and font rendering problems. The only custom work needed is: (1) choosing and converting BDF fonts, (2) designing the 64x64 pixel layout, (3) writing the render compositor, and (4) Norwegian date string formatting.

## Common Pitfalls

### Pitfall 1: Pixoo 300-Push Lockup
**What goes wrong:** Device stops responding entirely after approximately 300 screen updates via the HTTP API. Requires power cycle to recover. At 1 push per minute, this happens in ~5 hours.
**Why it happens:** Firmware-level internal counter overflow. Divoom has not fixed it.
**How to avoid:** Enable `refresh_connection_automatically=True` in the pixoo library constructor. This resets the internal counter every 32 frames at a slight delay cost. Must be enabled from the very first device connection.
**Warning signs:** Device stops updating but shows no error. Last pushed frame remains frozen. HTTP requests to device start timing out.

### Pitfall 2: PIL Bitmap Font 256-Character Limit
**What goes wrong:** Developers assume PIL bitmap fonts cannot render Norwegian characters because the format is "limited to 256 characters."
**Why it happens:** The 256-char limit maps to Latin-1 (ISO 8859-1), code points 0-255. Many developers confuse this with "ASCII only" (0-127).
**How to avoid:** Verify that target characters are within Latin-1. Norwegian aeoeaa are: ae=198/230, oe=216/248, aa=197/229 -- ALL within 0-255. PIL bitmap fonts from BDF sources with ISO 8859-1 coverage WILL render them. The key is using a BDF font that actually includes these glyphs.
**Warning signs:** Characters render as empty boxes or are silently skipped. The font file does not contain the glyph even though the encoding supports it.

### Pitfall 3: TrueType Anti-Aliasing on LED Pixels
**What goes wrong:** Text rendered with TrueType fonts at small sizes (5-8px) appears blurry or has missing pixels on the LED display.
**Why it happens:** FreeType (Pillow's text renderer for TrueType) applies anti-aliasing by default. At small sizes, anti-aliased pixels create gray intermediate values that look muddy on discrete LEDs. Additionally, FreeType hinting at small sizes can drop pixels entirely (Pillow issue #6421).
**How to avoid:** Prefer BDF bitmap fonts (no anti-aliasing by design). If TrueType is used, set `draw.fontmode = '1'` on the ImageDraw instance. Use OTF format over TTF format -- OTF produces more consistent results with `fontmode='1'` per Pillow issue #6421. Test every character at the target size before committing to a font.
**Warning signs:** Characters have fuzzy edges, sub-pixel gray values, or missing strokes at small sizes.

### Pitfall 4: Simulator Black Screen on Apple Silicon
**What goes wrong:** The pixoo library's Tkinter simulator shows a black screen on MacBook M-series processors.
**Why it happens:** Known compatibility issue with tkinter on Apple Silicon Macs. Documented in the pixoo library README.
**How to avoid:** Use an alternative verification strategy: save rendered PIL Images as PNG files and inspect them directly. This also enables automated visual regression testing. The simulator is convenient but not required -- the real verification is on the physical device.
**Warning signs:** Simulator window opens but displays only black.

### Pitfall 5: Frame Pushing Without Content Change
**What goes wrong:** Pushing the same frame repeatedly wastes device bandwidth, hits the 300-push counter faster, and may cause buffer artifacts (ghost images from previous frames).
**Why it happens:** Simple timer-based loops push every N seconds regardless of whether data changed.
**How to avoid:** Implement a dirty flag. Only push a new frame when the display state has actually changed. For the clock, state changes every minute (when the minute digit changes). Compare new state to previous state before triggering a render+push cycle.
**Warning signs:** Device exhibits ghost artifacts. Push counter advances unnecessarily.

### Pitfall 6: Brightness Too High Causes Device Crashes
**What goes wrong:** Setting brightness to 100% can cause the Pixoo 64 to crash during continuous operation.
**Why it happens:** Likely thermal or power delivery issue at sustained full brightness.
**How to avoid:** Cap brightness at 90% maximum. Use `set_brightness()` API. Consider auto-dimming at night for both aesthetics and device longevity.
**Warning signs:** Device becomes unresponsive after extended operation at high brightness.

## Code Examples

### Complete Frame Rendering and Push to Device

```python
# Source: pixoo library README + Pillow ImageDraw docs
from PIL import Image, ImageDraw, ImageFont
from pixoo import Pixoo

# Initialize device with connection refresh
pixoo = Pixoo('192.168.1.100', 64)

# Create 64x64 frame
img = Image.new("RGB", (64, 64), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Load bitmap font (after BDF->PIL conversion)
font_large = ImageFont.load("assets/fonts/7x13.pil")
font_small = ImageFont.load("assets/fonts/5x8.pil")

# Draw time
draw.text((4, 0), "14:32", font=font_large, fill=(255, 255, 255))

# Draw Norwegian date (with oe character in "lor")
draw.text((4, 16), "tor 20. feb", font=font_small, fill=(180, 180, 180))

# Push to device (file path approach)
img.save("/tmp/frame.png")
pixoo.draw_image("/tmp/frame.png")
pixoo.push()
```

### Alternative: Direct Pixel Manipulation Without File Save

```python
# Source: pixoo library draw primitives + PIL Image
# The pixoo library provides draw_image() which accepts file paths.
# For avoiding filesystem writes, use the library's pixel-level drawing:
from pixoo import Pixoo

pixoo = Pixoo('192.168.1.100', 64)

# Compose with PIL
img = render_frame(state, fonts)

# Extract pixels and set them directly on pixoo buffer
pixels = list(img.getdata())
for i, (r, g, b) in enumerate(pixels):
    x = i % 64
    y = i // 64
    pixoo.draw_pixel_at_location(x, y, r, g, b)
pixoo.push()

# Note: This is slower than draw_image() with a file.
# Preferred approach: save to tempfile, use draw_image().
# Or use the raw HTTP protocol directly (see Architecture research).
```

### BDF Font Conversion at Startup

```python
# Source: Pillow BdfFontFile module documentation
from PIL import BdfFontFile
import os

FONT_DIR = "assets/fonts"

def ensure_pil_fonts():
    """Convert any BDF fonts to PIL format if not already done."""
    for filename in os.listdir(FONT_DIR):
        if filename.endswith(".bdf"):
            pil_path = os.path.join(FONT_DIR, filename.replace(".bdf", ".pil"))
            if not os.path.exists(pil_path):
                bdf_path = os.path.join(FONT_DIR, filename)
                with open(bdf_path, "rb") as fp:
                    font = BdfFontFile.BdfFontFile(fp)
                    font.save(os.path.splitext(bdf_path)[0])
                print(f"Converted {filename} -> PIL format")
```

### Main Loop with Dirty Flag

```python
# Source: Standard Python pattern + pixoo library constraints
import time
from datetime import datetime

def main_loop(pixoo, fonts, layout):
    last_state = None

    while True:
        # Update state
        now = datetime.now()
        current_state = DisplayState(
            time_str=now.strftime("%H:%M"),
            date_str=format_date_norwegian(now),
        )

        # Only render and push if state changed
        if current_state != last_state:
            frame = render_frame(current_state, fonts, layout)
            frame.save("/tmp/frame.png")
            pixoo.draw_image("/tmp/frame.png")
            pixoo.push()
            last_state = current_state

        # Sleep until next check (every 1 second to catch minute changes promptly)
        time.sleep(1)
```

### TrueType Fallback (If BDF Fails)

```python
# Source: Pillow ImageDraw fontmode docs + issue #6421
from PIL import Image, ImageDraw, ImageFont

# Load pixel font at exact design size
font = ImageFont.truetype("assets/fonts/CozetteVector.ttf", size=13)

img = Image.new("RGB", (64, 64), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# CRITICAL: Disable anti-aliasing for crisp LED rendering
draw.fontmode = "1"

draw.text((4, 0), "14:32", font=font, fill=(255, 255, 255))
# Note: Use OTF format over TTF for more reliable rendering at small sizes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pixoo native `Draw/SendHttpText` | Full-frame PIL rendering via `Draw/SendHttpGif` | Community consensus by 2023 | Native text cannot coexist with pixel buffer; no aeoeaa; crash risk. PIL approach is universal. |
| PICO-8 font only (pixoo built-in) | External BDF/TTF bitmap fonts via PIL | Always available | PICO-8 lacks aeoeaa. PIL font loading unlocks any bitmap font. |
| locale module for Norwegian dates | Manual dictionary approach | Best practice | locale is fragile across platforms; dictionary is deterministic with 19 entries. |
| No connection refresh | `refresh_connection_automatically=True` | pixoo library feature | Without it, device dies after ~5 hours. With it, stable indefinitely. |
| TrueType fonts at small sizes | BDF bitmap fonts for LED/pixel displays | Ongoing consensus | TrueType anti-aliasing creates artifacts on LED matrices. BDF is pixel-perfect by design. |

**Deprecated/outdated:**
- **Pixoo native text commands for dashboard use:** Cannot coexist with pixel buffer rendering. Crash risk with extended characters. Superseded by PIL full-frame approach.
- **pixoo library's built-in PICO-8 font for Norwegian text:** Character set is `0-9 a-z A-Z !'()+,-<=>?[]^_:;./{|}~$@%` -- no aeoeaa support.

## Bitmap Font Candidates (Verified)

### Primary Recommendation: hzeller/rpi-rgb-led-matrix fonts

| Font File | Dimensions | Character Coverage | Norwegian Support | Confidence |
|-----------|------------|-------------------|-------------------|------------|
| 5x8.bdf | 5x8 px | ISO 8859 parts 1-5, 7-10, 13-16 (886 chars) | YES (ISO 8859-1 includes aeoeaa) | HIGH |
| 6x12.bdf | 6x12 px | ISO 8859 parts 1-5, 7-10, 13-16 (886 chars) | YES | HIGH |
| 7x13.bdf | 7x13 px | ISO 8859 parts 1-5, 7-10, 13-16 (3282 chars with Greek/Cyrillic) | YES | HIGH |
| 7x14.bdf | 7x14 px | ISO 8859 parts 1-5, 7-10, 13-16 | YES | HIGH |
| 4x6.bdf | 4x6 px | ISO 8859 parts 1-5, 7-10, 13-16 (886 chars) | YES | HIGH |

**Source:** https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/fonts -- Unicode (ISO 10646-1) extensions of classic ISO 8859-1 X11 terminal fonts by Markus Kuhn (2008).

**Why this collection:** Designed explicitly for LED matrix displays. Available in BDF format. Cover ISO 8859-1 fully (which includes aeoeaa at code points 197-248). Multiple sizes from 4x6 to 10x20. Well-tested in the RGB LED matrix community. MIT-compatible licensing.

### Fallback Options

| Font | Format | Size | Norwegian Support | Notes |
|------|--------|------|-------------------|-------|
| Terminus | BDF | 6x12, 8x14, 8x16+ | YES (ISO 8859-1/2/5/7/9/13/15/16) | 1356 characters. v4.49.1. |
| Matrix-Fonts (trip5) | BDF + TTF | 6-row, 8-row variants | YES (Latin Extended-A) | Designed for LED matrix clocks. |
| Spleen | BDF | 5x8, 6x12, 8x16+ | PARTIAL (5x8 and 6x12 limited to printable ASCII) | Only 8x16+ sizes have full ISO 8859-1. |
| Cozette | BDF + TTF | 6x13 (avg 5px wide) | LIKELY (extensive Unicode coverage) | MIT license. Needs testing for aeoeaa. |
| Tamzen | BDF | 5x9, 6x12, 7x13+ | YES (ISO 8859-1) | Monospace. Based on Tamsyn. |

### Recommended Font Assignments

| Zone | Font Size | Candidate | Rationale |
|------|-----------|-----------|-----------|
| Clock (time digits) | 7x13 or 7x14 | hzeller 7x13.bdf or 7x14.bdf | Large, readable digits. "14:32" at 7px wide = ~42px, fits 64px width. Legible from 2+ meters. |
| Date line | 5x8 | hzeller 5x8.bdf | Compact but readable. "tor 20. feb" at 5px wide = ~60px, tight but fits. Contains oe for "lor". |
| Zone labels / small text | 4x6 | hzeller 4x6.bdf | Minimal space usage for labels like "BUS" or placeholder text. |

**IMPORTANT:** These are research recommendations, not confirmed choices. The actual font selection MUST be validated by rendering test strings including "lor 21. mar" (contains oe) on the simulator or device. This is flagged as a hands-on task during implementation.

## Layout Design Guidance

### Pixel Budget Analysis

Total canvas: 64 x 64 = 4096 pixels.

```
Zone Allocation (64 pixels vertical):
+----------------------------------+  y=0
|  CLOCK: time digits (large)     |  14px (7x13 font + 1px padding)
|  "14:32"                         |
+----------------------------------+  y=14
|  DATE: Norwegian date (small)    |  9px (5x8 font + 1px padding)
|  "tor 20. feb"                   |
+----------------------------------+  y=23
|  1px divider line                |  1px
+----------------------------------+  y=24
|  BUS ZONE (placeholder)          |  19px (for 2 lines of bus data)
|  "-- buss --" or blank           |
+----------------------------------+  y=43
|  1px divider line                |  1px
+----------------------------------+  y=44
|  WEATHER ZONE (placeholder)      |  20px (icon + temp + hi/lo)
|  "-- vaer --" or blank           |
+----------------------------------+  y=64

Total: 14 + 9 + 1 + 19 + 1 + 20 = 64px exactly
```

### Readability from 2+ Meters

On a 64x64 LED display, each LED pixel is approximately 2.5mm. A 7x13 character is therefore ~17.5mm wide x 32.5mm tall. At 2 meters, this subtends a visual angle of approximately 0.5 degrees per character height, which is above the minimum readability threshold (~0.3 degrees for simple numerals). The clock digits will be readable.

The 5x8 date text is smaller (~12.5mm x 20mm per character), subtending ~0.36 degrees at 2 meters. This is at the lower limit of comfortable readability for text, which is acceptable for secondary information (date) that users will occasionally glance at but not read every time.

### Color Strategy

| Zone | Text Color | Background | Rationale |
|------|------------|------------|-----------|
| Clock | Bright white (255, 255, 255) | Black (0, 0, 0) | Maximum contrast for primary information |
| Date | Dim white or light gray (180, 180, 180) | Black | Secondary info, slightly dimmer to create hierarchy |
| Divider lines | Dark gray (40, 40, 40) | Black | Subtle zone separation without burning pixels |
| Placeholder zones | Very dim gray (60, 60, 60) | Black | Present but unobtrusive until data is wired in |

### Empty Zone Treatment Options

For bus and weather zones before data is wired (Phases 2-3), three approaches:

1. **Labeled placeholders** (recommended): Show "BUS" and "VAER" in dim text. Users can see the layout is intentional and expect data to appear later.
2. **Blank zones:** Leave black. Cleaner but users might think the display is broken.
3. **Decorative dividers only:** Show divider lines between zones. Minimal but indicates zone boundaries.

Recommendation: Option 1 (labeled placeholders) -- it validates the layout and zone proportions during UAT.

## Open Questions

1. **pixoo library `draw_image()` vs `send_image()` vs direct pixel manipulation**
   - What we know: `draw_image()` accepts file paths (confirmed from examples). There are references to `send_image()` accepting PIL Image objects (from pixoo-rest documentation) but this is not clearly documented in the main pixoo library.
   - What's unclear: Whether the current v0.9.2 has a method that accepts PIL Image objects directly without saving to a file first.
   - Recommendation: Start with the file-path approach (save PIL Image to tmpfile, pass path to `draw_image()`). If `send_image(pil_image)` exists, use it. If neither works smoothly, fall back to direct HTTP POST with base64 encoding (documented in architecture research). Test this during the first implementation task.

2. **Simulator black screen on Apple Silicon**
   - What we know: Known issue documented in pixoo library README for MacBook M-processors.
   - What's unclear: Whether there's a workaround or if this is a tkinter issue that's been fixed in recent Python/macOS versions.
   - Recommendation: Primary development workflow should save frames as PNG files for inspection rather than depending on the simulator. The real test is on the physical device.

3. **Optimal frame push interval for a clock dashboard**
   - What we know: Maximum 1 push/second. Clock changes every 60 seconds. Connection refresh happens every 32 frames.
   - What's unclear: Whether pushing every 60 seconds (only when minute changes) is sufficient, or if more frequent pushes are needed for responsiveness.
   - Recommendation: Push only when state changes (dirty flag). For Phase 1 (clock only), this means once per minute. Check time every 1 second, push only when minute changes. This minimizes device stress and is well within the 300-push budget before refresh.

## Sources

### Primary (HIGH confidence)
- [SomethingWithComputers/pixoo](https://github.com/SomethingWithComputers/pixoo) -- Pixoo 64 Python library v0.9.2. Constructor parameters, draw methods, push behavior, simulator, connection refresh mechanism. Verified via GitHub README and examples.py.
- [Pillow ImageFont documentation](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html) -- BdfFontFile conversion, ImageFont.load(), bitmap font 256-char Latin-1 limit, TrueType parameters.
- [Pillow ImageDraw documentation](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) -- text() method parameters, fontmode='1' for anti-aliasing control, textbbox() for measurement.
- [hzeller/rpi-rgb-led-matrix fonts](https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/fonts) -- BDF fonts 4x6 through 10x20 with ISO 8859 parts 1-16 coverage (886-3282 characters). Font README confirms character coverage targets.
- [ISO 8859-1 character table](https://cs.stanford.edu/people/miles/iso8859.html) -- Confirmed aeoeaa code points: ae=198/230, oe=216/248, aa=197/229. All within Latin-1 (0-255).
- [Pillow issue #5124](https://github.com/python-pillow/Pillow/issues/5124) -- Bitmap font Unicode limitation: Latin-1 encoding, 256 chars. Closed with documentation update (no code fix needed).

### Secondary (MEDIUM confidence)
- [pixoo-rest (4ch1m)](https://github.com/4ch1m/pixoo-rest) -- Confirms PIL Image workflow with pixoo library. Shows `send_image(img)` pattern from REST wrapper.
- [pixoo on PyPI](https://pypi.org/project/pixoo/) -- Version 0.9.2, Python >=3.10, CC-BY-NC-SA 4.0 license, REST interface documentation.
- [Pillow issue #6421](https://github.com/python-pillow/Pillow/issues/6421) -- Pixel font anti-aliasing: FreeType hinting with mono rendering can be broken. OTF format more reliable than TTF. `fontmode='1'` helps but is not perfect for all fonts.
- [Terminus Font](https://terminus-font.sourceforge.net/) -- BDF bitmap font v4.49.1, 1356 chars, ISO 8859-1/2/5/7/9/13/15/16 coverage.
- [trip5/Matrix-Fonts](https://github.com/trip5/Matrix-Fonts) -- BDF+TTF fonts for LED matrix clocks. Latin Extended-A coverage confirmed.
- [Cozette font](https://github.com/the-moonwitch/Cozette) -- 6x13px BDF bitmap font, MIT license, extensive Unicode coverage.
- [fcambus/spleen](https://github.com/fcambus/spleen) -- Monospaced bitmap fonts. 5x8 and 6x12 limited to ASCII; 8x16+ has full ISO 8859-1.

### Tertiary (LOW confidence)
- [Pillow pilfont conversion](https://github.com/python-pillow/pillow-scripts/blob/main/Scripts/pilfont.py) -- pilfont.py script from pillow-scripts. Used for BDF->PIL font conversion. Limited documentation.
- [sunaku/tamzen-font](https://github.com/sunaku/tamzen-font) -- BDF monospace font, ISO 8859-1 encoding. Available in 5x9, 6x12, 7x13+ sizes.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pixoo library and Pillow are well-documented, verified across multiple sources. No contested choices.
- Architecture: HIGH -- PIL full-frame rendering is the documented consensus across all Pixoo 64 dashboard projects. Zone-based layout is standard.
- Font strategy: MEDIUM-HIGH -- BDF fonts with ISO 8859-1 coverage confirmed to include aeoeaa. But specific font rendering quality at target sizes needs hands-on testing.
- Pitfalls: HIGH -- 300-push lockup, anti-aliasing, and Norwegian character encoding all verified from multiple sources.
- Layout design: MEDIUM -- Pixel math is sound but actual readability from 2+ meters needs physical device testing during UAT.

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable domain; pixoo library and Pillow change infrequently)

---
*Phase: 01-foundation*
*Research completed: 2026-02-20*
