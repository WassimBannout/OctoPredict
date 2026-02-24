import asyncio
import time


class TokenBucketRateLimiter:
    """Token bucket rate limiter for async code.

    Enforces at most `rate` requests per `period` seconds.
    """

    def __init__(self, rate: int = 10, period: float = 60.0) -> None:
        self.rate = rate
        self.period = period
        self.tokens = float(rate)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            # Refill tokens proportionally
            self.tokens = min(
                float(self.rate),
                self.tokens + elapsed * (self.rate / self.period),
            )
            self.last_refill = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) * (self.period / self.rate)
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0
