import os
import time
from collections.abc import Hashable

from app.tinder.client import TinderAPIError, TinderClient
from app.tinder.fake_client import FakeTinderClient


class TinderSessionManager:
    """Keeps one Tinder API client per user or web session in memory."""

    def __init__(self, ttl_seconds: float | None = None) -> None:
        self._clients: dict[Hashable, TinderClient] = {}
        self._last_seen: dict[Hashable, float] = {}
        self._api_mode = os.getenv("TINDER_API_MODE", "fake").lower()
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else float(os.getenv("SESSION_TTL_SECONDS", "3600"))

    def _is_expired(self, user_id: Hashable, now: float | None = None) -> bool:
        last_seen = self._last_seen.get(user_id)
        if last_seen is None:
            return False
        current_time = time.monotonic() if now is None else now
        return current_time - last_seen >= self._ttl_seconds

    def get_client(self, user_id: Hashable) -> TinderClient:
        if user_id not in self._clients or self._is_expired(user_id):
            self.remove(user_id)
            if self._api_mode == "real":
                self._clients[user_id] = TinderClient()
            else:
                self._clients[user_id] = FakeTinderClient()
        self._last_seen[user_id] = time.monotonic()
        return self._clients[user_id]

    def find_client(self, user_id: Hashable) -> TinderClient | None:
        if user_id not in self._clients:
            return None
        if self._is_expired(user_id):
            self.remove(user_id)
            return None
        self._last_seen[user_id] = time.monotonic()
        return self._clients[user_id]

    def get_authenticated_client(self, user_id: Hashable) -> TinderClient:
        client = self.get_client(user_id)
        if not client.is_authenticated:
            raise TinderAPIError("Tinder user is not authenticated.")
        return client

    def remove(self, user_id: Hashable) -> None:
        self._clients.pop(user_id, None)
        self._last_seen.pop(user_id, None)
