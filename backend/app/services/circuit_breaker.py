import time
import logging
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> State:
        if self._state == State.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
        return self._state

    def _record_success(self):
        self._failures = 0
        self._state = State.CLOSED
        self._opened_at = None

    def _record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "Circuit breaker '%s' OPEN after %d failures",
                self.name,
                self._failures,
            )

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Any = None,
        **kwargs,
    ) -> Any:
        if self.state == State.OPEN:
            logger.warning("Circuit breaker '%s' is OPEN — returning fallback", self.name)
            return fallback

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            logger.error("Circuit breaker '%s' recorded failure: %s", self.name, exc)
            if self.state == State.OPEN:
                return fallback
            raise


anthropic_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30, name="anthropic")
stripe_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, name="stripe")
supabase_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=15, name="supabase")
