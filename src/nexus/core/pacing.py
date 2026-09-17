"""Domain-aware pacing, rate limiting, and concurrency control.

Prevents rate limiting (HTTP 429/503) when opening multiple URLs from the
same domain without imposing artificial multi-second delays between different
domains or local operations.
"""

from __future__ import annotations

import asyncio
import random
import time
from urllib.parse import urlparse


class DomainPacer:
    """Manages dispatch pacing per domain to respect website rate limits."""

    def __init__(
        self,
        same_domain_delay_min: float = 0.35,
        same_domain_delay_max: float = 0.6,
        different_domain_delay: float = 0.2,
        max_same_domain_batch: int = 10,
        progressive_delay_increment: float = 0.2,
    ) -> None:
        self.same_domain_delay_min = same_domain_delay_min
        self.same_domain_delay_max = same_domain_delay_max
        self.different_domain_delay = different_domain_delay
        self.max_same_domain_batch = max_same_domain_batch
        self.progressive_delay_increment = progressive_delay_increment
        self._last_domain_dispatch: dict[str, float] = {}

    def extract_domain(self, url: str) -> str:
        """Extract normalized domain from a URL."""
        try:
            domain = urlparse(url).netloc.lower()
            return domain or "unknown"
        except Exception:
            return "unknown"

    def group_by_domain(self, urls: list[str]) -> dict[str, list[str]]:
        """Group URLs by their netloc/domain."""
        groups: dict[str, list[str]] = {}
        for url in urls:
            d = self.extract_domain(url)
            groups.setdefault(d, []).append(url)
        return groups

    def get_same_domain_delay(self, batch_index: int = 0) -> float:
        """Calculate randomized same-domain delay with progressive scaling."""
        base = random.uniform(self.same_domain_delay_min, self.same_domain_delay_max)
        progressive = batch_index * self.progressive_delay_increment
        jitter = random.uniform(0.1, 0.4)
        return base + progressive + jitter

    def get_cross_domain_delay(self) -> float:
        """Calculate minimal pleasant stagger for independent domains."""
        jitter = random.uniform(0.05, 0.15)
        return self.different_domain_delay + jitter

    async def wait_for_domain(self, domain: str, batch_index: int = 0) -> float:
        """Wait if necessary before dispatching to `domain`. Returns time slept."""
        now = time.monotonic()
        last = self._last_domain_dispatch.get(domain)

        needed_delay = 0.0
        if last is not None and domain != "unknown":
            target_delay = self.get_same_domain_delay(batch_index)
            elapsed = now - last
            if elapsed < target_delay:
                needed_delay = target_delay - elapsed

        if needed_delay > 0:
            await asyncio.sleep(needed_delay)

        self._last_domain_dispatch[domain] = time.monotonic()
        return needed_delay

    def record_dispatch(self, domain: str) -> None:
        """Record dispatch timestamp for a domain."""
        self._last_domain_dispatch[domain] = time.monotonic()

    def reset(self) -> None:
        """Clear all pacing history."""
        self._last_domain_dispatch.clear()

    @staticmethod
    def calculate_backoff(
        attempt: int,
        base_delay: float = 2.0,
        max_delay: float = 10.0,
    ) -> float:
        """Exponential backoff calculation with jitter for rate-limited retries."""
        calculated = base_delay * (2 ** (attempt - 1))
        capped = min(calculated, max_delay)
        jitter = random.uniform(0.2, 0.8)
        return capped + jitter
