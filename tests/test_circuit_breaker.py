"""Tests for the CircuitBreaker class."""

from unittest.mock import patch

from src.circuit_breaker import CircuitBreaker


class TestCircuitBreakerClosed:
    """Tests for CLOSED state (normal operation)."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == "closed"
        assert cb.should_attempt() is True

    def test_success_keeps_closed(self):
        cb = CircuitBreaker("test")
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_single_failure_stays_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.failure_count == 1
        assert cb.should_attempt() is True

    def test_failures_below_threshold_stay_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.should_attempt() is True


class TestCircuitBreakerOpen:
    """Tests for transition to and behavior in OPEN state."""

    def test_opens_at_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.should_attempt() is False

    def test_open_blocks_attempts(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.should_attempt() is False
        assert cb.should_attempt() is False

    def test_additional_failures_stay_open(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 5


class TestCircuitBreakerHalfOpen:
    """Tests for HALF_OPEN state (recovery probing)."""

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        with patch("src.circuit_breaker.time.monotonic", return_value=cb._opened_at + 11):
            assert cb.should_attempt() is True
            assert cb.state == "half_open"

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=10)
        cb.record_failure()
        cb.record_failure()

        with patch("src.circuit_breaker.time.monotonic", return_value=cb._opened_at + 11):
            cb.should_attempt()

        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=10)
        cb.record_failure()
        cb.record_failure()

        with patch("src.circuit_breaker.time.monotonic", return_value=cb._opened_at + 11):
            cb.should_attempt()

        cb.record_failure()
        assert cb.state == "open"

    def test_no_transition_before_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=100)
        cb.record_failure()
        cb.record_failure()

        with patch("src.circuit_breaker.time.monotonic", return_value=cb._opened_at + 50):
            assert cb.should_attempt() is False
            assert cb.state == "open"


class TestCircuitBreakerResetAfterRecovery:
    """Tests for reset behavior after recovery."""

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_intermittent_failures_dont_trip(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # resets
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.failure_count == 1
