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
uses a threading.Lock to allow safe access from multiple threads (e.g. main
loop and Discord bot thread).

All timing uses time.monotonic() for duration accuracy. Human-readable
timestamps use datetime.now(timezone.utc).
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config import HEALTH_DEBOUNCE, HEALTH_DEBOUNCE_DEFAULT

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
    bus_name_dir1: str | None = None,
    bus_name_dir2: str | None = None,
    weather_location: str | None = None,
):
    """Build a blue startup embed with config summary.

    Args:
        pixoo_ip: IP address of the Pixoo device.
        bus_quay_dir1: Quay ID for bus direction 1.
        bus_quay_dir2: Quay ID for bus direction 2.
        weather_lat: Weather location latitude.
        weather_lon: Weather location longitude.
        bus_name_dir1: Human-readable name for bus stop direction 1.
        bus_name_dir2: Human-readable name for bus stop direction 2.
        weather_location: Human-readable weather location name.

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
    embed.add_field(name="Pixoo IP", value=pixoo_ip, inline=False)

    bus1_label = f"Bus — {bus_name_dir1}" if bus_name_dir1 else "Bus Stop 1"
    bus2_label = f"Bus — {bus_name_dir2}" if bus_name_dir2 else "Bus Stop 2"
    embed.add_field(name=bus1_label, value=bus_quay_dir1, inline=True)
    embed.add_field(name=bus2_label, value=bus_quay_dir2, inline=True)

    if weather_location:
        weather_val = f"{weather_location} ({weather_lat}, {weather_lon})"
    else:
        weather_val = f"{weather_lat}, {weather_lon}"
    embed.add_field(name="Weather", value=weather_val, inline=False)

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

    @staticmethod
    def _log_embed_error(fut):
        """Done-callback for fire-and-forget embed sends.

        Consumes the future result so exceptions don't go unobserved,
        and logs failures at debug level (monitoring embeds are best-effort).
        """
        try:
            if not fut.cancelled():
                fut.result()
        except (OSError, RuntimeError) as exc:
            logger.warning("Failed to deliver embed to Discord: %s", exc)

    def send_embed(self, embed) -> bool:
        """Send an embed to the monitoring channel (fire-and-forget).

        Thread-safe and non-blocking. Returns True if the send was
        successfully **scheduled**, False if scheduling itself failed.
        NEVER propagates exceptions to the caller -- monitoring must not
        crash the main loop.

        When called from the event loop thread (e.g. from on_ready), schedules
        the send as a task. When called cross-thread, schedules via
        run_coroutine_threadsafe. In both cases the method returns immediately
        without waiting for delivery.

        Args:
            embed: discord.Embed to send.

        Returns:
            True if embed was successfully scheduled, False otherwise.
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

            # Detect if we're on the event loop thread.
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is self._client.loop:
                # On the event loop — schedule as a task (fire-and-forget).
                task = running_loop.create_task(coro)
                task.add_done_callback(self._log_embed_error)
                return True

            # Cross-thread — schedule fire-and-forget, don't block on result.
            fut = asyncio.run_coroutine_threadsafe(coro, self._client.loop)
            fut.add_done_callback(self._log_embed_error)
            return True
        except (OSError, RuntimeError) as exc:
            logger.warning("Failed to send monitoring embed: %s", exc)
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

    # Debounce configuration per component (imported from config):
    #   failures_before_alert: consecutive failures required before first alert
    #   repeat_interval: seconds between repeat alerts for ongoing failure
    DEBOUNCE = HEALTH_DEBOUNCE
    _DEFAULT_DEBOUNCE = HEALTH_DEBOUNCE_DEFAULT

    def __init__(self, monitor: MonitorBridge | None):
        """Initialize the health tracker.

        Args:
            monitor: MonitorBridge for sending embeds, or None to disable sends.
        """
        self._lock = threading.Lock()
        self._monitor = monitor
        self._components: dict[str, ComponentState] = {}
        self._created_at = time.monotonic()

    def set_monitor(self, monitor: MonitorBridge | None) -> None:
        """Set or replace the monitoring bridge (allows deferred initialization)."""
        with self._lock:
            self._monitor = monitor

    @property
    def uptime_s(self) -> float:
        """Seconds since this HealthTracker was created."""
        with self._lock:
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
        embed_to_send = None
        monitor = None

        with self._lock:
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
                # Was alerting -- prepare recovery embed (send outside lock)
                downtime = time.monotonic() - state.first_failure_time
                if self._monitor is not None:
                    embed_to_send = recovery_embed(component, downtime)
                    monitor = self._monitor

            # Reset failure state
            state.failure_count = 0
            state.is_alerting = False
            state.first_failure_time = 0.0
            state.last_success_time = time.monotonic()
            state.last_success_str = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )

        # Send embed outside the lock to avoid deadlocks
        if embed_to_send is not None:
            try:
                monitor.send_embed(embed_to_send)
            except (OSError, RuntimeError) as exc:
                logger.warning(
                    "Failed to send recovery embed for %s: %s", component, exc
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
        embed_to_send = None
        monitor = None

        with self._lock:
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
                if self._monitor is not None:
                    embed_to_send = error_embed(
                        component=component,
                        error_type=error_info.split(":")[0]
                        if ":" in error_info
                        else error_info,
                        detail=error_info,
                        duration_s=duration,
                        last_success_str=state.last_success_str,
                    )
                    monitor = self._monitor
                state.is_alerting = True
                state.last_alert_time = now

        # Send embed outside the lock to avoid deadlocks
        if embed_to_send is not None:
            try:
                monitor.send_embed(embed_to_send)
            except (OSError, RuntimeError) as exc:
                logger.warning(
                    "Failed to send error embed for %s: %s", component, exc
                )

    def get_status(self) -> dict[str, dict]:
        """Get per-component health status for the status command.

        Returns:
            Dict mapping component names to status dicts with keys:
                status: "ok" or "down"
                failure_count: int
                downtime_s: float (only if down)
                last_success: str (human-readable timestamp)
        """
        with self._lock:
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
