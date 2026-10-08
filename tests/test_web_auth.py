import pytest

from app.services.auth import AuthService
from app.services.session import TinderSessionManager
from app.services.web_auth import WebAuthService
from app.services.web_session import WebSessionStateStore
from app.tinder.client import TinderAPIError
from app.tinder.models import Location


def make_service():
    return WebAuthService(TinderSessionManager(), WebSessionStateStore())


def test_web_auth_uses_auth_service(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    service = make_service()
    calls = []

    def authenticate_with_token(self, token):
        calls.append(token)

    monkeypatch.setattr(AuthService, "authenticate_with_token", authenticate_with_token)

    session_id = service.authenticate_with_token("test-token")

    assert calls == ["test-token"]
    assert service.get_web_state(session_id) is not None


def test_token_auth_creates_authenticated_web_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    service = make_service()

    session_id = service.authenticate_with_token("test-token")

    client = service.get_authenticated_client(session_id)
    assert client.is_authenticated
    assert service.get_web_state(session_id) is not None


def test_phone_auth_binds_and_verifies_web_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    service = make_service()

    session_id = service.request_phone_code("+31612345678")
    assert service.web_sessions.find_by_phone("+31612345678") == session_id

    verified_session_id, token = service.verify_phone_code("+31612345678", "1234")

    assert verified_session_id == session_id
    assert token
    assert service.web_sessions.find_by_phone("+31612345678") is None
    assert service.get_authenticated_client(session_id).is_authenticated


def test_phone_verification_rejects_unknown_phone():
    service = make_service()

    with pytest.raises(TinderAPIError, match="Phone authentication session not found"):
        service.verify_phone_code("+31612345678", "1234")


def test_logout_removes_tinder_and_web_session(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    service = make_service()

    session_id = service.authenticate_with_token("test-token")
    service.web_sessions.set_location(
        session_id,
        "Amsterdam",
        Location(latitude=52.3676, longitude=4.9041, address="Amsterdam, Netherlands"),
    )

    service.logout(session_id)

    assert service.sessions.find_client(session_id) is None
    assert service.web_sessions.get(session_id) is None


def test_expired_web_session_cannot_be_authenticated(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    sessions = TinderSessionManager(ttl_seconds=60)
    service = WebAuthService(sessions, WebSessionStateStore())

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 100.0)
    session_id = service.authenticate_with_token("test-token")

    monkeypatch.setattr("app.services.session.time.monotonic", lambda: 161.0)

    with pytest.raises(TinderAPIError, match="not found or expired"):
        service.get_authenticated_client(session_id)
