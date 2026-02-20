"""Discord bot provider for persistent display message override.

Runs a Discord bot in a background daemon thread. Messages sent in the
configured channel appear on the Pixoo display. Sending 'clear' removes
the message. The bot is optional -- if DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID
is not set, it simply does not start.

Thread safety: MessageBridge uses a threading.Lock to safely pass messages
from the async Discord bot thread to the synchronous main rendering loop.
"""

import logging
import threading

logger = logging.getLogger(__name__)


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

        Args:
            text: Message text to display, or None to clear.
        """
        with self._lock:
            self._message = text

    @property
    def current_message(self) -> str | None:
        """Read the current message (thread-safe).

        Returns:
            Current message text, or None if no message is set.
        """
        with self._lock:
            return self._message


def run_discord_bot(bridge: MessageBridge, token: str, channel_id: int) -> None:
    """Run the Discord bot (blocking). Designed for background thread.

    Listens for messages in the configured channel. Any text message sets
    the display message. 'clear', 'cls', or 'reset' clears it. Reacts with
    a checkmark to confirm receipt.

    Args:
        bridge: MessageBridge to write messages to.
        token: Discord bot token.
        channel_id: Discord channel ID to listen on.
    """
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        logger.info("Discord bot connected as %s", client.user)

    @client.event
    async def on_message(message):
        # Ignore messages from other channels
        if message.channel.id != channel_id:
            return
        # Ignore own messages
        if message.author == client.user:
            return

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

    try:
        client.run(token, log_handler=None)  # Suppress discord.py's own logging setup
    except Exception:
        logger.exception("Discord bot crashed")


def start_discord_bot(token: str | None, channel_id: str | None) -> MessageBridge | None:
    """Start Discord bot in background thread. Returns MessageBridge or None.

    If token or channel_id is not provided, returns None (bot not started).
    The bot thread is a daemon -- it dies when the main process exits.

    Args:
        token: Discord bot token (from DISCORD_BOT_TOKEN env var).
        channel_id: Discord channel ID string (from DISCORD_CHANNEL_ID env var).

    Returns:
        MessageBridge instance if bot started, None if config missing.
    """
    if not token or not channel_id:
        return None

    bridge = MessageBridge()
    thread = threading.Thread(
        target=run_discord_bot,
        args=(bridge, token, int(channel_id)),
        daemon=True,
        name="discord-bot",
    )
    thread.start()
    return bridge
