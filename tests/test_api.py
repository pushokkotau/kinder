from fastapi.testclient import TestClient

from app.api import app, web_sessions


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
