"""Discord bot provider for persistent display message override.

Runs a Discord bot in a background daemon thread. Messages sent in the
configured channel appear on the Pixoo display. Sending 'clear' removes
the message. The bot is optional -- if DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID
is not set, it simply does not start.

Optionally supports a second monitoring channel for health alerts and on-demand
status queries. Monitoring is purely additive -- if DISCORD_MONITOR_CHANNEL_ID
is not set, the bot behaves exactly as before.

Thread safety: MessageBridge uses a threading.Lock to safely pass messages
from the async Discord bot thread to the synchronous main rendering loop.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.providers.discord_monitor import HealthTracker

logger = logging.getLogger(__name__)


def sanitize_for_bdf(text: str) -> str | None:
    """Strip characters that BDF bitmap fonts cannot render.

    BDF fonts only support Latin-1 (code points 0-255). Characters outside
    this range (emoji, CJK, etc.) cause UnicodeEncodeError in PIL's
    font.getbbox(). This function removes them before text reaches the
    renderer.

    Args:
        text: Raw message text (may contain emoji, Unicode, etc.).

    Returns:
        Sanitized text with only Latin-1 characters, or None if nothing
        renderable remains. Consecutive whitespace is collapsed.
    """
    # Remove all characters with code points > 255 (outside Latin-1)
    cleaned = "".join(ch for ch in text if ord(ch) <= 255)
    # Collapse any whitespace left behind by removed characters
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


class MessageBridge:
    """Thread-safe bridge for passing messages from Discord bot to main loop.

    The Discord bot writes messages via set_message(), and the main loop reads
    them via current_message. Both operations are protected by a threading.Lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._message: str | None = None

    def set_message(self, text: str | None) -> None:
        """Set or clear the current display message.

        Sanitizes text to remove characters outside Latin-1 (code points
        > 255) that BDF bitmap fonts cannot render. If only non-renderable
        characters remain, the message is cleared (set to None).

        Args:
            text: Message text to display, or None to clear.
        """
        with self._lock:
            self._message = sanitize_for_bdf(text) if text is not None else None

    @property
    def current_message(self) -> str | None:
        """Read the current message (thread-safe).

        Returns:
            Current message text, or None if no message is set.
        """
        with self._lock:
            return self._message


def run_discord_bot(
    bridge: MessageBridge,
    token: str,
    channel_id: int,
    *,
    monitor_channel_id: int | None = None,
    health_tracker: HealthTracker | None = None,
    on_ready_callback: Callable[[Any], None] | None = None,
    bot_dead_event: threading.Event | None = None,
) -> None:
    """Run the Discord bot (blocking). Designed for background thread.

    Listens for messages in the configured channel. Any text message sets
    the display message. 'clear', 'cls', or 'reset' clears it. Reacts with
    a checkmark to confirm receipt.

    Optionally listens on a monitoring channel for 'status' commands and
    delegates lifecycle events via on_ready_callback.

    Args:
        bridge: MessageBridge to write messages to.
        token: Discord bot token.
        channel_id: Discord channel ID to listen on for display messages.
        monitor_channel_id: Optional monitoring channel ID for health alerts.
        health_tracker: Optional HealthTracker for status command responses.
        on_ready_callback: Optional callable(client) invoked when bot is ready.
        bot_dead_event: Optional threading.Event set when the bot thread exits.
    """
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info("Discord bot connected as %s", client.user)
        # Signal "alive" only after the bot is actually connected, not before
        # attempting connection (avoids race in _run_discord_bot_with_retry).
        if bot_dead_event is not None:
            bot_dead_event.clear()
        if on_ready_callback is not None:
            try:
                await asyncio.get_event_loop().run_in_executor(None, on_ready_callback, client)
            except (discord.HTTPException, OSError, ValueError) as exc:
                logger.warning("on_ready_callback failed: %s", exc)

    @client.event
    async def on_message(message):
        # Ignore own messages
        if message.author == client.user:
            return

        # Display channel -- existing behavior (unchanged)
        if message.channel.id == channel_id:
            content = message.content.strip()
            if content.lower() in ("clear", "cls", "reset"):
                bridge.set_message(None)
                logger.info("Display message cleared via Discord")
            else:
                bridge.set_message(content)
                logger.info("Display message set: %s", content[:50])

            # React to confirm receipt
            try:
                await message.add_reaction("\u2713")
            except discord.HTTPException:
                logger.debug("Could not add reaction to message %s", message.id)

        # Monitoring channel -- status command
        if monitor_channel_id is not None and message.channel.id == monitor_channel_id:
            content = message.content.strip()
            if content.lower() == "status" and health_tracker is not None:
                try:
                    from src.providers.discord_monitor import status_embed

                    embed = status_embed(health_tracker.get_status(), health_tracker.uptime_s)
                    await message.channel.send(embed=embed)
                except discord.HTTPException:
                    logger.warning("Failed to send status embed")

                # React to confirm receipt
                try:
                    await message.add_reaction("\u2713")
                except discord.HTTPException:
                    logger.debug("Could not add reaction to message %s", message.id)

    try:
        client.run(token, log_handler=None)  # Suppress discord.py's own logging setup
        # client.run() returned normally -- bot disconnected
        logger.warning("Discord bot disconnected (client.run returned)")
    except (OSError, discord.ConnectionClosed, discord.HTTPException) as exc:
        logger.warning("Discord bot crashed: %s", exc)
        raise  # re-raise so the retry wrapper can catch it
    finally:
        if bot_dead_event is not None:
            bot_dead_event.set()


def _run_discord_bot_with_retry(
    bridge: MessageBridge,
    token: str,
    channel_id: int,
    **kwargs,
) -> None:
    """Wrap run_discord_bot with retry logic and exponential backoff.

    If run_discord_bot crashes (e.g. token revocation, extended outage),
    retries with exponential backoff up to 5 minutes. A clean disconnect
    (no exception) is not retried.
    """
    import discord

    backoff = 5
    max_retries = 20
    retries = 0
    while True:
        # NOTE: dead_event is cleared by the on_ready callback inside
        # run_discord_bot, not here, to avoid a race where the main loop
        # sees "alive" before the bot actually reconnects.
        try:
            run_discord_bot(bridge, token, channel_id, **kwargs)
            break  # clean disconnect, don't retry
        except (OSError, ConnectionError) as exc:
            retries += 1
            if retries >= max_retries:
                logger.critical("Discord bot failed %d times, giving up: %s", retries, exc)
                break
            jitter = random.uniform(0, backoff * 0.3)
            sleep_time = backoff + jitter
            logger.warning(
                "Discord bot crashed, retrying in %.0fs (attempt %d/%d)",
                sleep_time,
                retries,
                max_retries,
            )
            time.sleep(sleep_time)
            backoff = min(backoff * 2, 300)
        except (
            discord.HTTPException,
            discord.GatewayNotFound,
            discord.ConnectionClosed,
            RuntimeError,
        ) as exc:
            retries += 1
            if retries >= max_retries:
                logger.critical(
                    "Discord bot failed %d times with retryable error, giving up: %s",
                    retries,
                    exc,
                )
                break
            jitter = random.uniform(0, backoff * 0.3)
            sleep_time = backoff + jitter
            logger.warning(
                "Discord bot crashed (%s), retrying in %.0fs (attempt %d/%d)",
                exc,
                sleep_time,
                retries,
                max_retries,
            )
            time.sleep(sleep_time)
            backoff = min(backoff * 2, 300)
        except Exception as exc:
            logger.critical(
                "Discord bot hit unexpected error, not retrying: %s",
                exc,
                exc_info=True,
            )
            break


def start_discord_bot(
    token: str | None,
    channel_id: str | None,
    *,
    monitor_channel_id: str | None = None,
    health_tracker: HealthTracker | None = None,
    on_ready_callback: Callable[[Any], None] | None = None,
) -> tuple[MessageBridge, threading.Event] | None:
    """Start Discord bot in background thread. Returns (MessageBridge, Event) or None.

    If token or channel_id is not provided, returns None (bot not started).
    The bot thread is a daemon -- it dies when the main process exits.

    Monitoring is piggybacked on the same bot -- if the bot doesn't start
    (no token/channel_id), monitoring doesn't start either.

    Args:
        token: Discord bot token (from DISCORD_BOT_TOKEN env var).
        channel_id: Discord channel ID string (from DISCORD_CHANNEL_ID env var).
        monitor_channel_id: Optional monitoring channel ID string.
        health_tracker: Optional HealthTracker for status command.
        on_ready_callback: Optional callable(client) for bot ready event.

    Returns:
        Tuple of (MessageBridge, bot_dead_event) if bot started, None if
        config missing. The bot_dead_event is set when the bot thread exits
        (crash or normal disconnect).
    """
    if not token or not channel_id:
        return None

    try:
        parsed_channel_id = int(channel_id)
    except ValueError:
        logger.error("DISCORD_CHANNEL_ID is not a valid integer: %r", channel_id)
        return None

    monitor_id = None
    if monitor_channel_id:
        try:
            monitor_id = int(monitor_channel_id)
        except ValueError:
            logger.warning(
                "DISCORD_MONITOR_CHANNEL_ID is not a valid integer: %r, ignoring",
                monitor_channel_id,
            )

    bridge = MessageBridge()
    bot_dead_event = threading.Event()
    thread = threading.Thread(
        target=_run_discord_bot_with_retry,
        args=(bridge, token, parsed_channel_id),
        kwargs={
            "monitor_channel_id": monitor_id,
            "health_tracker": health_tracker,
            "on_ready_callback": on_ready_callback,
            "bot_dead_event": bot_dead_event,
        },
        daemon=True,
        name="discord-bot",
    )
    thread.start()
    return bridge, bot_dead_event
