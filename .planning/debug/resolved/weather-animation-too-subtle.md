---
status: complete
type: debug-session
target: weather animation visibility on Pixoo 64
symptom: "I don't see it, it might be too subtle"
uat_test: 4
started: 2026-02-20
---

# Debug Session: Weather Animation Too Subtle / Invisible

## Symptom

UAT Test 4 expected a visible animated weather background in the 64x20 weather zone. User reported they could not see any animation at all.

## Investigation

### 1. Alpha Values Are Extremely Low

All animation particle/shape alpha values are in the range 15-50 out of 255:

| Animation     | Shape              | Alpha | % Opacity |
|---------------|--------------------|-------|-----------|
| RainAnimation | 1px raindrop       | 50    | 19.6%     |
| SnowAnimation | 1px snowflake      | 45    | 17.6%     |
| CloudAnimation| ellipse (primary)  | 35    | 13.7%     |
| CloudAnimation| ellipse (secondary)| 30    | 11.8%     |
| SunAnimation  | ellipse glow       | 15-35 | 5.9-13.7% |
| ThunderAnim   | flash rectangle    | 40    | 15.7%     |
| FogAnimation  | fog line bands     | 30-45 | 11.8-17.6%|

On a black background (0,0,0), a rain drop at alpha 50 means the pixel value is `(80*50/255, 160*50/255, 255*50/255)` = approximately `(16, 31, 50)` RGB. These are extremely dim values -- barely distinguishable from pure black on a small LED matrix.

### 2. Compositing Logic Cancels Most of the Effect (PRIMARY ROOT CAUSE)

In `renderer.py` lines 128-137, the compositing code is:

```python
if anim_frame is not None:
    img.paste(
        Image.alpha_composite(
            Image.new("RGBA", anim_frame.size, (0, 0, 0, 255)),
            anim_frame,
        ).convert("RGB"),
        (0, zone_y),
        mask=anim_frame.split()[3],  # use alpha channel as mask
    )
```

This does the following:
1. Creates a fully opaque black RGBA image `(0, 0, 0, 255)`
2. Alpha-composites the animation frame ON TOP of it -- this blends the low-alpha animation pixels over solid black, producing very dim RGB values (correct so far, but values are tiny)
3. Converts the result to RGB
4. Pastes that RGB result onto the main image using the **animation alpha channel as a paste mask**

Step 4 is the critical problem. The `mask` parameter in `Image.paste()` controls how much of the source replaces the destination. With alpha values of 30-50, the paste mask means only 12-20% of those already-dim pixels actually reach the destination. The effect is essentially DOUBLE alpha application:

- First alpha application: `alpha_composite` blends animation over black, producing dim pixels like RGB(16, 31, 50)
- Second alpha application: `paste(mask=alpha)` blends those dim pixels over the existing black background at only 50/255 = 19.6% strength, producing final values like RGB(3, 6, 10)

The resulting pixel values are so close to black (0,0,0) that they are literally invisible on an LED display.

**Example calculation for a single rain drop pixel:**
- Animation pixel: RGBA(80, 160, 255, 50)
- After alpha_composite over black: RGB(80*50/255, 160*50/255, 255*50/255) = RGB(15.7, 31.4, 50.0)
- After paste with mask alpha=50: destination_pixel * (1 - 50/255) + source_pixel * (50/255)
  = (0,0,0) * 0.804 + (15.7, 31.4, 50.0) * 0.196 = RGB(3.1, 6.2, 9.8)
- **Final pixel value: approximately RGB(3, 6, 10) -- essentially invisible**

### 3. Rate Limiter Drops Most Animation Frames

In `pixoo_client.py` lines 62-66:

```python
if self._last_push_time > 0 and elapsed < 1.0:
    logger.warning(
        "Push skipped: only %.2fs since last push (minimum 1s interval)"
    )
    return
```

The main loop in `main.py` line 153 sets `sleep_time = 0.25` when animation is active, attempting 4 FPS. However, the PixooClient enforces a minimum 1-second interval between pushes. This means **3 out of every 4 animation frames are silently dropped**. The effective animation rate is ~1 FPS, not 4 FPS.

At 1 FPS, rain drops that fall 2-3 pixels per tick appear to jump/teleport rather than smoothly fall. Snow flakes (1-2 pixels per tick) are similarly jerky. This compounds the visibility problem -- even if alpha were correct, the animation would look like occasional random pixel flickers rather than smooth particle motion.

### 4. Particle Count and Size Are Extremely Small

On a 64x20 pixel zone (1,280 total pixels):

| Animation   | Particles | Pixels per particle | Total pixels lit | % of zone |
|-------------|-----------|---------------------|------------------|-----------|
| Rain        | 18        | 1 (point)           | 18               | 1.4%      |
| Snow        | 15        | 1 (point)           | 15               | 1.2%      |
| Cloud       | 3         | ~60 (ellipse)       | ~180             | 14.1%     |
| Sun         | 1         | ~100 (ellipse)      | ~100             | 7.8%      |
| Fog         | 4         | ~50 (line)          | ~200             | 15.6%     |

Rain and Snow use single-pixel particles. On a 64-LED-wide display, 15-18 single pixels at alpha 50 (effectively alpha ~10 after double compositing) are completely invisible. Even cloud and sun which have larger shapes are nearly invisible due to the double-alpha issue.

### 5. Weather Zone Background is Pure Black

The base image is `Image.new("RGB", (64, 64), color=(0, 0, 0))`. The weather zone has no background color of its own. The animation particles are attempting to add tiny amounts of color to pure black, making them even harder to perceive. On an LED matrix, the LEDs simply stay OFF for such low values -- there is a minimum brightness threshold below which LEDs produce no visible light.

## Root Causes (Ranked by Impact)

### PRIMARY: Double Alpha Application in Compositing (renderer.py:128-137)

The `alpha_composite()` followed by `paste(mask=alpha_channel)` applies the alpha transparency TWICE, squaring the effective opacity. A pixel intended to be at 20% opacity ends up at ~4% opacity. This alone makes all animations invisible.

### SECONDARY: Rate Limiter Drops 75% of Frames (pixoo_client.py:62-66)

The 1-second rate limit in PixooClient conflicts with the 0.25-second animation loop. Only 1 in 4 frames reaches the display, making smooth animation impossible and reducing even further the chance of noticing any effect.

### CONTRIBUTING: Alpha Values Are Too Conservative (weather_anim.py)

Even without the double-alpha bug, alpha values of 30-50 produce very dim pixels on a black background. On LED hardware, pixel values below ~15-20 per channel may not produce visible light. The design intent of "subtle" overshoots into "invisible" territory.

### CONTRIBUTING: Rain/Snow Use Single-Pixel Particles (weather_anim.py)

Single `draw.point()` calls for rain/snow mean each particle is exactly 1 pixel. At the effective brightness levels, individual pixels are invisible on the Pixoo 64. Even at correct alpha, single bright pixels on a 64px display are hard to see from viewing distance.

## Files Involved

- `src/display/renderer.py:128-137` -- Double alpha application in compositing logic
- `src/device/pixoo_client.py:62-66` -- 1-second rate limit drops 75% of animation frames
- `src/display/weather_anim.py` -- All animation alpha values (30-50) are too low; rain/snow use 1px particles
- `src/main.py:152-153` -- 0.25s sleep expects 4 FPS but device only accepts 1 FPS

## Suggested Fix Direction

1. **Fix compositing (highest priority):** Replace the double-alpha paste with a simple direct alpha composite. Either:
   - Use `Image.alpha_composite()` on an RGBA version of the base image, then convert to RGB
   - Or paste the pre-composited RGB result WITHOUT using the alpha mask (remove `mask=` parameter)

2. **Align frame rate:** Either increase the rate limiter to allow ~4 FPS, or slow the animation loop to ~1 FPS and increase particle movement per tick to compensate.

3. **Increase alpha values:** Raise all animation alphas to the 80-150 range. Test empirically on hardware to find the sweet spot where animation is visible but does not obscure text.

4. **Make rain/snow particles larger:** Use 2x2 or 2x1 pixel rectangles instead of single points. Consider adding a very dim "trail" pixel behind moving particles for continuity.
