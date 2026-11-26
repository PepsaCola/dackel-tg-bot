import time
from collections import defaultdict, deque


class RateLimiter:
    """Обмеження в пам'яті за принципом ковзного вікна: не більше `limit` запитів за `window` секунд з одного ключа."""

    _MAX_KEYS = 10_000

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Повертає True, якщо запит дозволено."""
        now = time.monotonic()
        if len(self._hits) > self._MAX_KEYS:
            self._cleanup(now)

        timestamps = self._hits[key]
        while timestamps and now - timestamps[0] > self._window:
            timestamps.popleft()

        if len(timestamps) >= self._limit:
            return False

        timestamps.append(now)
        return True

    def _cleanup(self, now: float) -> None:
        stale = [k for k, q in self._hits.items() if not q or now - q[-1] > self._window]
        for key in stale:
            del self._hits[key]