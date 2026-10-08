from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebSessionState:
    city: str | None = None
    location: Any | None = None
    phones: set[str] = field(default_factory=set)


class WebSessionStateStore:
    """Keeps web-only state separate from Tinder API client sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, WebSessionState] = {}
        self._phone_sessions: dict[str, str] = {}

    def create(self, session_id: str) -> WebSessionState:
        state = WebSessionState()
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> WebSessionState | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> WebSessionState:
        return self._sessions.setdefault(session_id, WebSessionState())

    def set_location(self, session_id: str, city: str, location: Any) -> None:
        state = self.get_or_create(session_id)
        state.city = city
        state.location = location

    def bind_phone(self, phone: str, session_id: str) -> None:
        state = self.get_or_create(session_id)
        previous_session_id = self._phone_sessions.get(phone)
        if previous_session_id and previous_session_id != session_id:
            previous_state = self.get(previous_session_id)
            if previous_state:
                previous_state.phones.discard(phone)

        self._phone_sessions[phone] = session_id
        state.phones.add(phone)

    def find_by_phone(self, phone: str) -> str | None:
        return self._phone_sessions.get(phone)

    def unbind_phone(self, phone: str) -> None:
        self._phone_sessions.pop(phone, None)

    def remove(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if state:
            for phone in state.phones:
                self._phone_sessions.pop(phone, None)

    def clear(self) -> None:
        self._sessions.clear()
        self._phone_sessions.clear()
