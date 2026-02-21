---
status: resolved
trigger: "The _draw_partcloud_night() function still uses the old ellipse-based moon that produces an unrecognizable blob at 10x10px"
created: 2026-02-21T12:00:00Z
updated: 2026-02-21T12:05:00Z
---

## Current Focus

hypothesis: CONFIRMED -- ellipse math at 5px scale produces blob; pixel bitmap produces clean crescent
test: Replaced ellipse moon with 10-pixel hand-crafted crescent bitmap
expecting: Clean crescent visible in top-left, cloud overlaps naturally
next_action: Archive session

## Symptoms

expected: The partly cloudy night icon should show a recognizable small crescent moon peeking behind a cloud, using hand-crafted pixel art like the standalone moon icon.
actual: The moon portion uses draw.ellipse([0, 0, 4, 4]) with a crescent cut via draw.ellipse([1, -1, 5, 3], fill=(0, 0, 0, 0)) which produces a blob on the LED display. Also uses cold silver color (200, 210, 220) instead of warm golden yellow.
errors: No errors -- visual quality issue only.
reproduction: Run the dashboard at night with partly cloudy conditions (current condition in Trondheim).
started: The standalone moon was fixed in commit 767ac20 but _draw_partcloud_night() was not updated at the same time.

## Eliminated

## Evidence

- timestamp: 2026-02-21T12:00:00Z
  checked: weather_icons.py lines 208-218 (_draw_partcloud_night)
  found: Uses draw.ellipse([0, 0, 4, 4]) for moon body and draw.ellipse([1, -1, 5, 3], fill=(0,0,0,0)) for crescent cut. Color is (200, 210, 220, 200) -- cold silver.
  implication: Same ellipse-math approach that was already identified as bad in the standalone _draw_moon() (commit 767ac20). The fix was applied to _draw_moon() but missed here.

- timestamp: 2026-02-21T12:01:00Z
  checked: weather_icons.py lines 91-128 (_draw_moon)
  found: Already uses hand-crafted 10x10 pixel bitmap with warm golden yellow (255, 220, 100, 255). This is the reference approach that works well on LED.
  implication: Need a scaled-down ~5x5 version of the same crescent technique for the partly cloudy night icon's moon portion.

- timestamp: 2026-02-21T12:01:00Z
  checked: weather_icons.py lines 196-205 (_draw_partcloud_day)
  found: Daytime version uses simple filled ellipse for sun -- works fine because a sun is just a circle. Crescent moon is the problem shape.
  implication: Cloud portion (ellipses at [2,3,7,8] and [4,2,9,7]) works fine and should be kept as-is. Only the moon portion needs replacing.

- timestamp: 2026-02-21T12:04:00Z
  checked: Pixel output of fixed icon via get_weather_icon('partlycloudy_night', 10)
  found: Clean crescent visible in rows 0-4 of top-left corner. Moon pixels at (2,0),(3,0),(1,1),(2,1),(0,2),(1,2),(0,3),(1,3),(1,4),(2,4) all render with correct warm golden yellow (255,220,100,255). Cloud naturally overlaps lower-right moon area creating "peeking behind" effect. Cloud pixels unchanged.
  implication: Fix produces a recognizable crescent at LED scale. Visual composition works -- moon peeks out from behind cloud.

- timestamp: 2026-02-21T12:05:00Z
  checked: Full test suite (112 tests)
  found: All 112 tests pass with zero failures.
  implication: No regressions introduced.

## Resolution

root_cause: _draw_partcloud_night() uses ellipse math (lines 213-214) for the crescent moon at ~5px scale, producing rasterization artifacts. The standalone _draw_moon() was fixed with a pixel bitmap in commit 767ac20 but this mini version was missed. Additionally uses wrong color (cold silver vs warm golden yellow).
fix: Replaced the two ellipse calls (moon body + crescent cut) with a 10-pixel hand-crafted crescent bitmap using putpixel(). Changed moon color from cold silver (200, 210, 220, 200) to warm golden yellow (255, 220, 100, 255) matching the standalone _draw_moon(). Cloud portion left completely unchanged.
verification: Pixel-by-pixel output inspection confirms clean crescent in top-left corner with natural cloud overlap. All 112 existing tests pass.
files_changed: [src/display/weather_icons.py]
