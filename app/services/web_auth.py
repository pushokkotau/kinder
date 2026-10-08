from uuid import uuid4

from app.services.auth import AuthService
from app.services.session import TinderSessionManager
from app.services.web_session import WebSessionState, WebSessionStateStore
from app.tinder.client import TinderAPIError, TinderClient


class WebAuthService:
    """Coordinates web authentication and web/Tinder session lifecycle."""

    def __init__(
        self,
        sessions: TinderSessionManager,
        web_sessions: WebSessionStateStore,
    ) -> None:
        self.sessions = sessions
        self.web_sessions = web_sessions

    def create_web_session(self) -> tuple[str, TinderClient]:
        session_id = uuid4().hex
        client = self.sessions.get_client(session_id)
        self.web_sessions.create(session_id)
        return session_id, client

    def authenticate_with_token(self, token: str) -> str:
        session_id, client = self.create_web_session()
        try:
            AuthService(client).authenticate_with_token(token)
        except (TinderAPIError, ValueError):
            self.remove_session(session_id)
            raise
        return session_id

    def request_phone_code(self, phone: str) -> str:
        session_id, client = self.create_web_session()
        try:
            AuthService(client).request_phone_code(phone)
        except (TinderAPIError, ValueError):
            self.remove_session(session_id)
            raise
        self.web_sessions.bind_phone(phone, session_id)
        return session_id

    def verify_phone_code(self, phone: str, code: str) -> tuple[str, str]:
        session_id = self.web_sessions.find_by_phone(phone)
        if session_id is None:
            raise TinderAPIError("Phone authentication session not found")

        client = self.sessions.find_client(session_id)
        if client is None:
            self.web_sessions.remove(session_id)
            raise TinderAPIError("Phone authentication session not found")

        try:
            token = AuthService(client).authenticate_with_code(phone, code)
        except (TinderAPIError, ValueError):
            raise

        state = self.web_sessions.get(session_id)
        if state:
            state.phones.discard(phone)
        self.web_sessions.unbind_phone(phone)
        return session_id, token

    def get_authenticated_client(self, session_id: str) -> TinderClient:
        try:
            return self.sessions.get_authenticated_client(session_id)
        except TinderAPIError:
            raise

    def get_web_state(self, session_id: str) -> WebSessionState | None:
        return self.web_sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        self.sessions.remove(session_id)
        self.web_sessions.remove(session_id)

    def logout(self, session_id: str) -> None:
        if self.sessions.find_client(session_id) is None:
            raise TinderAPIError("Invalid session token")
        self.remove_session(session_id)
