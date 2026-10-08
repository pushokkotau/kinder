from aiogram.types import Message

from app.services.factory import ClientServices, ServiceFactory
from app.services.session import TinderSessionManager


class TelegramServiceProvider:
    """Build application services for a Telegram user's Tinder session."""

    def __init__(self, sessions: TinderSessionManager):
        self.sessions = sessions

    def for_message(
        self,
        message: Message,
        *,
        authenticated: bool = False,
    ) -> ClientServices:
        user_id = message.from_user.id
        if authenticated:
            client = self.sessions.get_authenticated_client(user_id)
        else:
            client = self.sessions.get_client(user_id)
        return ServiceFactory.for_client(client)
