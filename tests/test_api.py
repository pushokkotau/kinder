from fastapi.testclient import TestClient

from app.tinder.client import TinderAPIError

from app.api import (
    app,
    sessions,
    web_sessions,
)


client = TestClient(app)


def authenticate():
    response = client.post("/api/v1/auth/token", json={"token": "test-token"})
    assert response.status_code == 200
    return response.json()["session_token"]


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoints_require_auth():
    response = client.get("/api/v1/profile")
    assert response.status_code == 401


def test_invalid_session_does_not_create_client():
    session_id = "missing-session"
    sessions.remove(session_id)

    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {session_id}"},
    )

    assert response.status_code == 401
    assert sessions.find_client(session_id) is None


def test_frontend_flow_with_fake_api(monkeypatch):
    monkeypatch.setenv("TINDER_API_MODE", "fake")
    web_sessions.clear()

    token = authenticate()
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/api/v1/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["name"] == "Тестовый пользователь"

    matches_before = client.get("/api/v1/matches/count", headers=headers)
    assert matches_before.json()["count"] == 10

    recommendations = client.get("/api/v1/recommendations", headers=headers)
    assert recommendations.status_code == 200
    items = recommendations.json()["recommendations"]
    assert len(items) == 6
    assert items[0]["id"] == "fake-user-1"

    swipe = client.post(
        f"/api/v1/swipes/like/{items[0]['id']}",
        headers=headers,
    )
    assert swipe.status_code == 200

    matches_after = client.get("/api/v1/matches/count", headers=headers)
    assert matches_after.json()["count"] == 11


def test_invalid_swipe_action():
    token = authenticate()
    response = client.post(
        "/api/v1/swipes/wow/user-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_autoswipe_reuses_resolved_location(monkeypatch):
    web_sessions.clear()

    class FakeLocation:
        address = "Amsterdam"
        latitude = 52.3676
        longitude = 4.9041

    geocode_calls = 0

    def set_city(self, city):
        nonlocal geocode_calls
        geocode_calls += 1
        self.client.set_location(FakeLocation.latitude, FakeLocation.longitude)
        return FakeLocation()

    monkeypatch.setattr("app.api.LocationService.set_city", set_city)

    token = authenticate()
    headers = {"Authorization": f"Bearer {token}"}

    location = client.post(
        "/api/v1/location",
        json={"city": "Amsterdam"},
        headers=headers,
    )
    assert location.status_code == 200
    assert geocode_calls == 1

    result = client.post("/api/v1/autoswipe", headers=headers)
    assert result.status_code == 200
    data = result.json()

    assert geocode_calls == 1
    assert data["matches_before"] == 10
    assert data["matches_after"] == 16
    assert data["new_matches"] == 6
    assert data["swipes"] == 12
    assert data["likes"] == 6
    assert data["dislikes"] == 6
    assert data["recommendations_received"] == 12
    assert data["recommendations_exhausted"] is True


def test_logout_removes_web_session_state():
    web_sessions.clear()

    token = authenticate()
    headers = {"Authorization": f"Bearer {token}"}
    web_sessions.set_location(token, "Amsterdam", object())
    web_sessions.bind_phone("+31612345678", token)

    response = client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}
    assert sessions.find_client(token) is None
    assert web_sessions.get(token) is None
    assert web_sessions.find_by_phone("+31612345678") is None


def test_logout_rejects_unknown_session():
    session_id = "missing-session"
    sessions.remove(session_id)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {session_id}"},
    )

    assert response.status_code == 401


def test_token_auth_maps_tinder_api_error_to_401(monkeypatch):
    def fail_authenticate(self, token):
        raise TinderAPIError("invalid token")

    monkeypatch.setattr(
        "app.api.TinderClient.authenticate_with_token",
        fail_authenticate,
    )

    response = client.post("/api/v1/auth/token", json={"token": "test-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid token"


def test_phone_auth_maps_tinder_api_error_to_400(monkeypatch):
    def fail_request(self, phone):
        raise TinderAPIError("invalid phone")

    monkeypatch.setattr(
        "app.api.TinderClient.request_auth_phone",
        fail_request,
    )

    response = client.post("/api/v1/auth/phone", json={"phone": "+31612345678"})

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid phone"
