"""LRU cache for high-confidence FAQ responses keyed by intent + language."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from app.schemas.chat import ChatMessageResponse


@dataclass
class _CacheEntry:
    response: ChatMessageResponse
    cached_at: float


class ResponseCache:
    """Thread-safe LRU cache for FAQ responses.

    Invalidated globally when knowledge documents are reindexed.
    """

    def __init__(self, max_size: int = 200, ttl_seconds: float = 3600) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(self, intent: str, language: str) -> str:
        return f"{intent}:{language}"

    def get(self, intent: str, language: str, min_confidence: float = 0.9) -> ChatMessageResponse | None:
        key = self._make_key(intent, language)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry.cached_at > self._ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.response

    def put(self, intent: str, language: str, response: ChatMessageResponse, confidence: float) -> None:
        if confidence < 0.9:
            return
        intent_type = intent
        cacheable_intents = {
            "faq",
            "studio_info",
            "hours",
            "pricing_guidance",
            "aftercare",
            "policies",
            "service_info",
        }
        if intent_type not in cacheable_intents:
            return

        key = self._make_key(intent, language)
        with self._lock:
            self._store[key] = _CacheEntry(response=response, cached_at=time.monotonic())
            self._store.move_to_end(key)
            if len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def invalidate_all(self) -> None:
        with self._lock:
            self._store.clear()


response_cache = ResponseCache()
