"""Discord monitoring module for remote health observability.

Provides three components:
1. Embed builder functions -- create color-coded Discord embeds for errors,
   recovery, startup, shutdown, and status events.
2. MonitorBridge -- thread-safe sync-to-async bridge that sends embeds to a
   dedicated monitoring channel from the synchronous main loop.
3. HealthTracker -- per-component failure/recovery state machine with debounced
   alerting. Tracks consecutive failures, only alerts after configurable
   thresholds, and emits recovery embeds when failed components recover.

Thread safety: MonitorBridge uses asyncio.run_coroutine_threadsafe() to safely
schedule async Discord sends from the synchronous main thread. HealthTracker
is designed for single-threaded use from the main loop.

All timing uses time.monotonic() for duration accuracy. Human-readable
timestamps use datetime.now(timezone.utc).
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embed color constants
# ---------------------------------------------------------------------------

COLORS = {
    "error": 0xFF0000,      # Red -- problems
    "recovery": 0x00FF00,   # Green -- recovered
    "startup": 0x3498DB,    # Blue -- lifecycle info
    "shutdown": 0x95A5A6,   # Gray -- lifecycle info
}

# ---------------------------------------------------------------------------
# Embed builder functions
# ---------------------------------------------------------------------------


def error_embed(
    component: str,
    error_type: str,
    detail: str,
    duration_s: float,
    last_success_str: str,
):
    """Build a red error embed with diagnostic context.

    Args:
        component: Name of the failing component (e.g. "bus_api").
        error_type: Short error classification (e.g. "TimeoutError").
        detail: Human-readable error detail.
        duration_s: Seconds since first consecutive failure.
        last_success_str: Human-readable timestamp of last success.

    Returns:
        discord.Embed with red color and diagnostic fields.
    """
    import discord

    embed = discord.Embed(
        title=f"Error: {component}",
        description=detail,
        color=COLORS["error"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Component", value=component, inline=True)
    embed.add_field(name="Error Type", value=error_type, inline=True)
    embed.add_field(name="Failing For", value=f"{duration_s:.0f}s", inline=True)
    embed.add_field(name="Last Success", value=last_success_str, inline=True)
    embed.set_footer(text="Divoom Hub Monitor")
    return embed


def recovery_embed(component: str, downtime_s: float):
    """Build a green recovery embed with downtime duration.

    Args:
        component: Name of the recovered component.
        downtime_s: Total downtime in seconds.

    Returns:
        discord.Embed with green color and downtime info.
    """
    import discord

    minutes = downtime_s / 60
    embed = discord.Embed(
        title=f"Recovered: {component}",
        description=f"{component} recovered after {minutes:.0f} minutes",
        color=COLORS["recovery"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Downtime", value=f"{minutes:.0f} minutes", inline=True)
    embed.set_footer(text="Divoom Hub Monitor")
    return embed


def startup_embed(
    pixoo_ip: str,
    bus_quay_dir1: str,
    bus_quay_dir2: str,
    weather_lat: float,
    weather_lon: float,
):
    """Build a blue startup embed with config summary.

    Args:
        pixoo_ip: IP address of the Pixoo device.
        bus_quay_dir1: Quay ID for bus direction 1.
        bus_quay_dir2: Quay ID for bus direction 2.
        weather_lat: Weather location latitude.
        weather_lon: Weather location longitude.

    Returns:
        discord.Embed with blue color and config fields.
    """
    import discord

    embed = discord.Embed(
        title="Divoom Hub Started",
        description="Dashboard is online",
        color=COLORS["startup"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Pixoo IP", value=pixoo_ip, inline=True)
    embed.add_field(
        name="Bus Stops", value=f"{bus_quay_dir1}, {bus_quay_dir2}", inline=True
    )
    embed.add_field(
        name="Weather Location", value=f"{weather_lat}, {weather_lon}", inline=True
    )
    embed.set_footer(text="Divoom Hub Monitor")
    return embed


def shutdown_embed():
    """Build a gray shutdown embed.

    Returns:
        discord.Embed with gray color indicating graceful shutdown.
    """
    import discord

    embed = discord.Embed(
        title="Divoom Hub Stopped",
        description="Dashboard is shutting down",
        color=COLORS["shutdown"],
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Divoom Hub Monitor")
    return embed


def status_embed(components_dict: dict, uptime_s: float):
    """Build a blue status embed showing per-component health.

    Args:
        components_dict: Dict of component name -> status info dict with keys:
            status (str "ok"/"down"), failure_count (int),
            downtime_s (float, if down), last_success (str).
        uptime_s: Total uptime in seconds since tracker creation.

    Returns:
        discord.Embed with blue color and per-component status fields.
    """
    import discord

    hours = int(uptime_s // 3600)
    mins = int((uptime_s % 3600) // 60)

    embed = discord.Embed(
        title="Divoom Hub Status",
        description=f"Uptime: {hours}h {mins}m",
        color=COLORS["startup"],
        timestamp=datetime.now(timezone.utc),
    )

    for name, info in components_dict.items():
        if info["status"] == "down":
            downtime = info.get("downtime_s", 0)
            value = f"DOWN ({downtime:.0f}s)"
        else:
            value = "OK"
        embed.add_field(name=name, value=value, inline=True)

    embed.set_footer(text="Divoom Hub Monitor")
    return embed


# ---------------------------------------------------------------------------
# MonitorBridge -- thread-safe sync-to-async embed sender
# ---------------------------------------------------------------------------


class MonitorBridge:
    """Thread-safe bridge for sending monitoring embeds from the sync main loop.

    The main rendering loop is synchronous (runs in the main thread with
    time.sleep ticks), while discord.py's channel.send() is async. This bridge
    uses asyncio.run_coroutine_threadsafe() to safely schedule embed sends on
    the Discord bot's event loop from any thread.

    Usage:
        bridge = MonitorBridge(client, channel_id)
        success = bridge.send_embed(some_embed)
    """

    def __init__(self, client, channel_id: int):
        """Initialize the monitor bridge.

        Args:
            client: discord.Client instance (must already be running).
            channel_id: ID of the Discord monitoring channel.
        """
        self._client = client
        self._channel_id = channel_id

    def send_embed(self, embed) -> bool:
        """Send an embed to the monitoring channel.

        Thread-safe and non-blocking (up to 5s timeout). Returns True on
        success, False on any failure. NEVER propagates exceptions to the
        caller -- monitoring must not crash the main loop.

        Args:
            embed: discord.Embed to send.

        Returns:
            True if embed was delivered, False otherwise.
        """
        import asyncio

        try:
            channel = self._client.get_channel(self._channel_id)
            if channel is None:
                logger.warning(
                    "Monitor channel %d not found in cache", self._channel_id
                )
                return False
            coro = channel.send(embed=embed)
            fut = asyncio.run_coroutine_threadsafe(coro, self._client.loop)
            fut.result(timeout=5.0)
            return True
        except Exception:
            logger.exception("Failed to send monitoring embed")
            return False


# ---------------------------------------------------------------------------
# HealthTracker -- debounced per-component failure/recovery state machine
# ---------------------------------------------------------------------------


@dataclass
class ComponentState:
    """Tracks health state for one monitored component."""

    name: str
    first_failure_time: float = 0.0
    last_alert_time: float = 0.0
    failure_count: int = 0
    is_alerting: bool = False
    last_success_time: float = field(default_factory=time.monotonic)
    last_success_str: str = "never"


class HealthTracker:
    """Tracks component health and emits debounced alerts via MonitorBridge.

    The HealthTracker is the brain of the monitoring system. It decides WHEN to
    alert (after N consecutive failures) and WHAT to include (component, error
    type, duration, last success). It sends recovery embeds when previously
    failed components succeed again.

    If monitor is None, state tracking still works but no embeds are sent.
    This allows the tracker to run without a Discord connection (useful for
    testing and when monitoring is disabled).

    Usage:
        tracker = HealthTracker(monitor=bridge)  # or monitor=None
        tracker.record_failure("bus_api", "TimeoutError: connect timed out")
        tracker.record_success("bus_api")
    """

    # Debounce configuration per component:
    #   failures_before_alert: consecutive failures required before first alert
    #   repeat_interval: seconds between repeat alerts for ongoing failure
    DEBOUNCE = {
        "bus_api": {"failures_before_alert": 3, "repeat_interval": 900},
        "weather_api": {"failures_before_alert": 2, "repeat_interval": 1800},
        "device": {"failures_before_alert": 5, "repeat_interval": 300},
    }
    _DEFAULT_DEBOUNCE = {"failures_before_alert": 3, "repeat_interval": 600}

    def __init__(self, monitor: MonitorBridge | None):
        """Initialize the health tracker.

        Args:
            monitor: MonitorBridge for sending embeds, or None to disable sends.
        """
        self._monitor = monitor
        self._components: dict[str, ComponentState] = {}
        self._created_at = time.monotonic()

    @property
    def uptime_s(self) -> float:
        """Seconds since this HealthTracker was created."""
        return time.monotonic() - self._created_at

    def _get_debounce(self, component: str) -> dict:
        """Get debounce config for a component, with defaults for unknown."""
        return self.DEBOUNCE.get(component, self._DEFAULT_DEBOUNCE)

    def _get_or_create_state(self, component: str) -> ComponentState:
        """Get existing component state or create a new one."""
        if component not in self._components:
            self._components[component] = ComponentState(name=component)
        return self._components[component]

    def record_success(self, component: str) -> None:
        """Record a successful operation for a component.

        If the component was previously alerting (is_alerting=True), sends a
        recovery embed with the total downtime duration. Resets failure state
        regardless.

        Args:
            component: Name of the component that succeeded.
        """
        state = self._components.get(component)
        if state is None:
            # First time seeing this component -- just record success
            self._components[component] = ComponentState(
                name=component,
                last_success_time=time.monotonic(),
                last_success_str=datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
            )
            return

        if state.is_alerting:
            # Was alerting -- send recovery embed
            downtime = time.monotonic() - state.first_failure_time
            try:
                if self._monitor is not None:
                    embed = recovery_embed(component, downtime)
                    self._monitor.send_embed(embed)
            except Exception:
                logger.exception(
                    "Failed to send recovery embed for %s", component
                )

        # Reset failure state
        state.failure_count = 0
        state.is_alerting = False
        state.first_failure_time = 0.0
        state.last_success_time = time.monotonic()
        state.last_success_str = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

    def record_failure(self, component: str, error_info: str) -> None:
        """Record a failed operation for a component.

        Increments the failure counter. When consecutive failures reach the
        debounce threshold and either (a) no alert has been sent yet, or
        (b) the repeat interval has elapsed since the last alert, sends an
        error embed.

        Args:
            component: Name of the component that failed.
            error_info: Human-readable error description.
        """
        state = self._get_or_create_state(component)
        now = time.monotonic()
        debounce = self._get_debounce(component)

        if state.failure_count == 0:
            state.first_failure_time = now

        state.failure_count += 1

        threshold = debounce["failures_before_alert"]
        repeat_interval = debounce["repeat_interval"]

        should_alert = False
        if state.failure_count >= threshold:
            if not state.is_alerting:
                # First alert for this failure sequence
                should_alert = True
            elif (now - state.last_alert_time) >= repeat_interval:
                # Repeat alert after interval elapsed
                should_alert = True

        if should_alert:
            duration = now - state.first_failure_time
            try:
                if self._monitor is not None:
                    embed = error_embed(
                        component=component,
                        error_type=error_info.split(":")[0]
                        if ":" in error_info
                        else error_info,
                        detail=error_info,
                        duration_s=duration,
                        last_success_str=state.last_success_str,
                    )
                    self._monitor.send_embed(embed)
            except Exception:
                logger.exception(
                    "Failed to send error embed for %s", component
                )
            state.is_alerting = True
            state.last_alert_time = now

    def get_status(self) -> dict[str, dict]:
        """Get per-component health status for the status command.

        Returns:
            Dict mapping component names to status dicts with keys:
                status: "ok" or "down"
                failure_count: int
                downtime_s: float (only if down)
                last_success: str (human-readable timestamp)
        """
        result = {}
        now = time.monotonic()
        for name, state in self._components.items():
            entry: dict = {
                "status": "down" if state.is_alerting else "ok",
                "failure_count": state.failure_count,
                "last_success": state.last_success_str,
            }
            if state.is_alerting and state.first_failure_time > 0:
                entry["downtime_s"] = now - state.first_failure_time
            result[name] = entry
        return result
