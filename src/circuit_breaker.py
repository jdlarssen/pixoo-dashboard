"""Circuit breaker for external API calls.

Prevents hammering failing APIs by tracking consecutive failures and
backing off when the failure threshold is reached. Three states:

- CLOSED (normal): requests flow through.
- OPEN (failing): requests blocked for ``reset_timeout`` seconds.
- HALF_OPEN (testing): one probe request allowed to test recovery.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker with three states: CLOSED, OPEN, HALF_OPEN."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        reset_timeout: float = 300,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.state = "closed"
        self._opened_at = 0.0
        self._lock = threading.Lock()

    def record_success(self) -> None:
        """Record a successful API call -- reset to CLOSED."""
        with self._lock:
            if self.state != "closed":
                logger.info(
                    "%s circuit breaker CLOSED -- service recovered",
                    self.name,
                )
            self.failure_count = 0
            self.state = "closed"

    def record_failure(self) -> None:
        """Record a failed API call -- may transition to OPEN."""
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                if self.state != "open":
                    logger.warning(
                        "%s circuit breaker OPEN -- backing off for %.0fs",
                        self.name,
                        self.reset_timeout,
                    )
                self.state = "open"
                self._opened_at = time.monotonic()

    def should_attempt(self) -> bool:
        """Return True if a request should be attempted."""
        with self._lock:
            if self.state == "closed":
                return True
            if self.state == "open":
                if time.monotonic() - self._opened_at >= self.reset_timeout:
                    self.state = "half_open"
                    logger.info(
                        "%s circuit breaker testing recovery...",
                        self.name,
                    )
                    return True
                return False
            # half_open: allow one attempt
            return True
