import pytest

from app.services.session import TinderSessionManager
from app.tinder.client import TinderAPIError


def test_get_authenticated_client_rejects_unauthenticated_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()

    with pytest.raises(TinderAPIError, match="not authenticated"):
        sessions.get_authenticated_client(1)


def test_authenticated_client_is_reused_for_same_user(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()
    client = sessions.get_client(1)
    client.authenticate_with_token("test-token")

    assert sessions.get_authenticated_client(1) is client


def test_sessions_are_isolated_between_users(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()

    first = sessions.get_client(1)
    second = sessions.get_client(2)

    assert first is not second
