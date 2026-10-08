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


def test_authenticated_client_does_not_recreate_expired_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager(ttl_seconds=60)
    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 100.0)

    client = sessions.get_client("web-session")
    client.authenticate_with_token("test-token")

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 161.0)

    with pytest.raises(TinderAPIError, match="not found or expired"):
        sessions.get_authenticated_client("web-session")

    assert sessions.find_client("web-session") is None


def test_sessions_are_isolated_between_users(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()

    first = sessions.get_client(1)
    second = sessions.get_client(2)

    assert first is not second


def test_web_session_identifier_is_supported(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()

    client = sessions.get_client("web-session")
    client.authenticate_with_token("test-token")

    assert sessions.find_client("web-session") is client
    assert sessions.get_authenticated_client("web-session") is client


def test_find_client_does_not_create_unknown_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager()

    assert sessions.find_client("missing") is None


def test_inactive_session_expires(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager(ttl_seconds=60)
    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 100.0)

    client = sessions.get_client("web-session")
    client.authenticate_with_token("test-token")

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 161.0)

    assert sessions.find_client("web-session") is None


def test_active_session_refreshes_last_seen(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager(ttl_seconds=60)
    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 100.0)

    client = sessions.get_client("web-session")
    client.authenticate_with_token("test-token")

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 150.0)
    assert sessions.find_client("web-session") is client

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 205.0)
    assert sessions.find_client("web-session") is client

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 266.0)
    assert sessions.find_client("web-session") is None
