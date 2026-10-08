import os
from collections.abc import Hashable

from app.tinder.client import TinderAPIError, TinderClient
from app.tinder.fake_client import FakeTinderClient


class TinderSessionManager:
    """Keeps one Tinder API client per user or web session in memory."""

    def __init__(self) -> None:
        self._clients: dict[Hashable, TinderClient] = {}
        self._api_mode = os.getenv("TINDER_API_MODE", "fake").lower()

    def get_client(self, user_id: Hashable) -> TinderClient:
        if user_id not in self._clients:
            if self._api_mode == "real":
                self._clients[user_id] = TinderClient()
            else:
                self._clients[user_id] = FakeTinderClient()
        return self._clients[user_id]

    def find_client(self, user_id: Hashable) -> TinderClient | None:
        return self._clients.get(user_id)

    def get_authenticated_client(self, user_id: Hashable) -> TinderClient:
        client = self.get_client(user_id)
        if not client.is_authenticated:
            raise TinderAPIError("Tinder user is not authenticated.")
        return client

    def remove(self, user_id: Hashable) -> None:
        self._clients.pop(user_id, None)
