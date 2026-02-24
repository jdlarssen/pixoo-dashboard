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

import logging
import re
import threading

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
    health_tracker=None,
    on_ready_callback=None,
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
    """
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info("Discord bot connected as %s", client.user)
        if on_ready_callback is not None:
            try:
                on_ready_callback(client)
            except Exception:
                logger.exception("on_ready_callback failed")

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
            except Exception:
                pass

        # Monitoring channel -- status command
        if monitor_channel_id is not None and message.channel.id == monitor_channel_id:
            content = message.content.strip()
            if content.lower() == "status" and health_tracker is not None:
                try:
                    from src.providers.discord_monitor import status_embed

                    embed = status_embed(
                        health_tracker.get_status(), health_tracker.uptime_s
                    )
                    await message.channel.send(embed=embed)
                except Exception:
                    logger.exception("Failed to send status embed")

                # React to confirm receipt
                try:
                    await message.add_reaction("\u2713")
                except Exception:
                    pass

    try:
        client.run(token, log_handler=None)  # Suppress discord.py's own logging setup
    except Exception:
        logger.exception("Discord bot crashed")


def start_discord_bot(
    token: str | None,
    channel_id: str | None,
    *,
    monitor_channel_id: str | None = None,
    health_tracker=None,
    on_ready_callback=None,
) -> MessageBridge | None:
    """Start Discord bot in background thread. Returns MessageBridge or None.

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
        MessageBridge instance if bot started, None if config missing.
    """
    if not token or not channel_id:
        return None

    bridge = MessageBridge()
    monitor_id = int(monitor_channel_id) if monitor_channel_id else None
    thread = threading.Thread(
        target=run_discord_bot,
        args=(bridge, token, int(channel_id)),
        kwargs={
            "monitor_channel_id": monitor_id,
            "health_tracker": health_tracker,
            "on_ready_callback": on_ready_callback,
        },
        daemon=True,
        name="discord-bot",
    )
    thread.start()
    return bridge
