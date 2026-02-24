# Device Keep-Alive + Auto-Recovery

## Problem

The Divoom Pixoo 64 disconnects from WiFi daily, requiring manual rebinding via the Divoom app. The ESP32 inside the device likely enters WiFi power save mode during idle periods between frame pushes. When the device goes offline, no Discord notification is sent (fixed separately) and the display freezes on the last successful frame.

## Solution

Two-layer approach: periodic health pings to keep the WiFi radio active, and graduated auto-recovery when failures are detected.

## Design

### 1. Periodic Health Ping

- New `ping()` method on `PixooClient` using `Channel/GetAllConf` command
- Lightweight (~50-100ms round-trip), no visual side-effect on the display
- Called every ~30 seconds from the main loop
- Keeps ESP32 WiFi radio from entering power save between frame pushes
- Respects existing rate limiting and error cooldown

### 2. Graduated Recovery

When consecutive ping/push failures accumulate:

| Failures | Action |
|----------|--------|
| 1-4 | Normal retry with existing 3s cooldown |
| 5 | Attempt `Device/SysReboot` via API |
| 5 + 30s wait | Resume pinging to check if device recovered |
| Reboot fails | Discord alert (already implemented via health tracker) |

- New `reboot()` method on `PixooClient` using `Device/SysReboot` command
- Reboot attempt is best-effort (device may not respond if truly offline)
- After reboot, wait 30s for device to reconnect to WiFi before resuming

### 3. Main Loop Integration

- Track last ping time; ping every 30s when no frame push happened recently
- Frame pushes reset the ping timer (a successful push proves connectivity)
- Ping failures feed into existing health tracker for Discord alerting

## Files to Modify

- `src/device/pixoo_client.py` -- add `ping()` and `reboot()` methods
- `src/main.py` -- integrate 30s ping cycle, reboot recovery logic

## Out of Scope

- Threading or async (stays synchronous)
- Network scanning / IP discovery (user will set static DHCP)
- New dependencies
- Config file changes
