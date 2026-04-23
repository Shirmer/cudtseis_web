from __future__ import annotations

from copy import deepcopy
import threading
import time
from typing import Generic, TypeVar


T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, T]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> T | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            timestamp, payload = item
            if now - timestamp > self.ttl_seconds:
                self._items.pop(key, None)
                return None
            return deepcopy(payload)

    def put(self, key: str, payload: T) -> None:
        with self._lock:
            self._items[key] = (time.time(), deepcopy(payload))
