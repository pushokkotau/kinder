import os
from typing import Dict

from app.tinder.client import TinderClient
from app.tinder.fake_client import FakeTinderClient


class TinderSessionManager:
    """Keeps one Tinder API client per Telegram user in memory."""

    def __init__(self):
        self._clients: Dict[int, TinderClient] = {}
        self._api_mode = os.getenv("TINDER_API_MODE", "fake").lower()

    def get_client(self, telegram_user_id: int) -> TinderClient:
        if telegram_user_id not in self._clients:
            if self._api_mode == "real":
                self._clients[telegram_user_id] = TinderClient()
            else:
                self._clients[telegram_user_id] = FakeTinderClient()
        return self._clients[telegram_user_id]

    def remove(self, telegram_user_id: int) -> None:
        self._clients.pop(telegram_user_id, None)
