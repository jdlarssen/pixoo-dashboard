"""Tests for Discord bot message sanitization and MessageBridge."""

from src.providers.discord_bot import MessageBridge, sanitize_for_bdf


class TestSanitizeForBdf:
    """Tests for sanitize_for_bdf() -- strips non-Latin-1 characters."""

    def test_plain_ascii_unchanged(self):
        """Pure ASCII text passes through unchanged."""
        assert sanitize_for_bdf("Hello world") == "Hello world"

    def test_norwegian_chars_preserved(self):
        """Norwegian characters (within Latin-1) are preserved."""
        assert sanitize_for_bdf("Kl\u00e6bo \u00e5 g\u00e5") == "Kl\u00e6bo \u00e5 g\u00e5"

    def test_emoji_stripped(self):
        """Emoji characters are removed."""
        assert sanitize_for_bdf("Gull! \U0001f604") == "Gull!"

    def test_multiple_emoji_stripped(self):
        """Multiple emoji are all removed."""
        assert sanitize_for_bdf("\U0001f3c6 Gull! \U0001f604\U0001f389") == "Gull!"

    def test_all_emoji_returns_none(self):
        """Message that is ALL emoji returns None (nothing renderable)."""
        assert sanitize_for_bdf("\U0001f604\U0001f389\U0001f525") is None

    def test_emoji_between_words_collapses_whitespace(self):
        """Emoji between words leaves clean single space."""
        assert sanitize_for_bdf("Hello \U0001f604 world") == "Hello world"

    def test_cjk_characters_stripped(self):
        """CJK characters (outside Latin-1) are stripped."""
        assert sanitize_for_bdf("Test \u4e16\u754c") == "Test"

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert sanitize_for_bdf("") is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only string returns None."""
        assert sanitize_for_bdf("   ") is None

    def test_latin1_boundary_char_preserved(self):
        """Character at code point 255 (Latin-1 max) is preserved."""
        # U+00FF is 'y with diaeresis' -- last Latin-1 character
        assert sanitize_for_bdf("\u00ff") == "\u00ff"

    def test_just_above_latin1_stripped(self):
        """Character at code point 256 (just outside Latin-1) is stripped."""
        # U+0100 is 'A with macron' -- first non-Latin-1 character
        assert sanitize_for_bdf("\u0100") is None

    def test_mixed_latin1_and_emoji(self):
        """Mixed Latin-1 and emoji keeps only Latin-1."""
        result = sanitize_for_bdf("Klaebo vant UL-gull!!! \U0001f604")
        assert result == "Klaebo vant UL-gull!!!"

    def test_flag_emoji_stripped(self):
        """Flag emoji (regional indicators, surrogate pairs) are stripped."""
        # Norwegian flag: U+1F1F3 U+1F1F4
        assert sanitize_for_bdf("\U0001f1f3\U0001f1f4 Norge") == "Norge"


class TestMessageBridgeSanitization:
    """Tests for MessageBridge.set_message() sanitization integration."""

    def test_set_none_clears_message(self):
        """Setting None clears the message."""
        bridge = MessageBridge()
        bridge.set_message("Hello")
        bridge.set_message(None)
        assert bridge.current_message is None

    def test_set_clean_text(self):
        """Clean ASCII text is stored as-is."""
        bridge = MessageBridge()
        bridge.set_message("Hello world")
        assert bridge.current_message == "Hello world"

    def test_set_emoji_text_sanitized(self):
        """Emoji text is sanitized before storage."""
        bridge = MessageBridge()
        bridge.set_message("Gull! \U0001f604")
        assert bridge.current_message == "Gull!"

    def test_set_all_emoji_becomes_none(self):
        """All-emoji message becomes None (cleared)."""
        bridge = MessageBridge()
        bridge.set_message("\U0001f604\U0001f389")
        assert bridge.current_message is None

    def test_set_norwegian_text_preserved(self):
        """Norwegian characters are preserved through sanitization."""
        bridge = MessageBridge()
        bridge.set_message("H\u00e6rlig v\u00e6r p\u00e5 \u00d8ya!")
        assert bridge.current_message == "H\u00e6rlig v\u00e6r p\u00e5 \u00d8ya!"
