import pytest
import requests

from app.tinder.client import TinderAPIError, TinderClient


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", content=b""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self.content = content

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return self._json_data


class FakeSession:
    def __init__(self, responses=None):
        self.headers = {}
        self.responses = list(responses or [])
        self.calls = []

    def request(self, method, url, timeout, **kwargs):
        self.calls.append(
            {"method": method, "url": url, "timeout": timeout, "kwargs": kwargs}
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_set_token_rejects_empty_token():
    client = TinderClient()

    with pytest.raises(ValueError, match="must not be empty"):
        client.set_token("   ")


def test_token_authentication_sets_header():
    client = TinderClient()

    client.authenticate_with_token("  test-token  ")

    assert client.is_authenticated
    assert client.session.headers["X-Auth-Token"] == "test-token"


def test_request_wraps_http_errors():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession(
        [FakeResponse(status_code=401, text="unauthorized")]
    )

    with pytest.raises(
        TinderAPIError, match=r"Tinder API returned 401: unauthorized"
    ):
        client.get_matches_count()


def test_request_wraps_network_errors():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession([requests.Timeout("timed out")])

    with pytest.raises(TinderAPIError, match="Tinder request failed"):
        client.get_matches_count()


def test_phone_authentication_extracts_token_from_response_bytes():
    token = "token-ä"
    payload = b"prefix\x12$" + token.encode() + b"\x22\x18suffix"

    client = TinderClient(base_url="https://example.test")
    session = FakeSession([FakeResponse(content=payload)])
    client.session = session

    result = client.authenticate_with_phone_code("+31612345678", "1234")

    assert result == token
    assert client.session.headers["X-Auth-Token"] == token
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == (
        "https://example.test/v3/auth/login?locale=ru"
    )


def test_phone_authentication_fails_when_token_is_missing():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession([FakeResponse(content=b"no-token-here")])

    with pytest.raises(TinderAPIError, match="did not contain an auth token"):
        client.authenticate_with_phone_code("+31612345678", "1234")


def test_get_profile_parses_city_and_country():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": {
                        "user": {
                            "name": "Alice",
                            "pos_info": {
                                "state": {"name": "Amsterdam"},
                                "country": {"name": "Netherlands"},
                            },
                        }
                    }
                }
            )
        ]
    )

    profile = client.get_profile()

    assert profile.name == "Alice"
    assert profile.city == "Amsterdam"
    assert profile.country == "Netherlands"


def test_get_profile_falls_back_when_location_is_missing():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession(
        [
            FakeResponse(
                json_data={"data": {"user": {"name": "Alice"}}}
            )
        ]
    )

    profile = client.get_profile()

    assert profile.city == "Город не определен"
    assert profile.country == ""


def test_get_recommendations_maps_users_and_skips_invalid_items():
    client = TinderClient(base_url="https://example.test")
    client.session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": {
                        "results": [
                            {
                                "user": {
                                    "_id": "user-1",
                                    "name": "Alice",
                                    "photos": [{"url": "1"}],
                                },
                                "s_number": 7,
                            },
                            {"user": {}},
                        ]
                    }
                }
            )
        ]
    )

    recommendations = client.get_recommendations()

    assert len(recommendations) == 1
    assert recommendations[0].user.id == "user-1"
    assert recommendations[0].user.name == "Alice"
    assert recommendations[0].s_number == 7
    assert recommendations[0].raw["user"]["_id"] == "user-1"


def test_set_location_sends_coordinates():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession([FakeResponse()])
    client.session = session

    client.set_location(52.3676, 4.9041)

    call = session.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://example.test/v2/meta?locale=ru"
    assert call["kwargs"]["json"] == {
        "lat": 52.3676,
        "lon": 4.9041,
        "force_fetch_resources": True,
    }


def test_like_and_dislike_use_expected_endpoints():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession([FakeResponse(), FakeResponse()])
    client.session = session

    client.like("user-1")
    client.dislike("user-2", s_number=42)

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://example.test/like/user-1?locale=ru"
    assert session.calls[1]["method"] == "POST"
    assert session.calls[1]["url"] == (
        "https://example.test/pass/user-2?locale=ru&s_number=42"
    )


def test_get_matches_count_follows_pagination():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": "1"}, {"id": "2"}],
                        "next_page_token": "page-2",
                    }
                }
            ),
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": "3"}],
                    }
                }
            ),
        ]
    )
    client.session = session

    assert client.get_matches_count() == 3
    assert session.calls[0]["url"] == (
        "https://example.test/v2/matches?locale=ru&count=100&is_tinder_u=false"
    )
    assert session.calls[1]["url"] == (
        "https://example.test/v2/matches?locale=ru&count=100&is_tinder_u=false"
        "&page_token=page-2"
    )


def test_get_matches_count_returns_zero_for_empty_matches():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession(
        [FakeResponse(json_data={"data": {"matches": []}})]
    )
    client.session = session

    assert client.get_matches_count() == 0
    assert len(session.calls) == 1


def test_get_matches_count_handles_multiple_pages_and_counts_all_matches():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": str(i)} for i in range(100)],
                        "next_page_token": "page-2",
                    }
                }
            ),
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": str(i)} for i in range(100, 200)],
                        "next_page_token": "page-3",
                    }
                }
            ),
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": str(i)} for i in range(200, 201)],
                    }
                }
            ),
        ]
    )
    client.session = session

    assert client.get_matches_count() == 201
    assert len(session.calls) == 3
    assert session.calls[1]["url"].endswith("&page_token=page-2")
    assert session.calls[2]["url"].endswith("&page_token=page-3")


def test_get_matches_count_stops_after_page_without_next_token():
    client = TinderClient(base_url="https://example.test")
    session = FakeSession(
        [
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": "1"}],
                        "next_page_token": "page-2",
                    }
                }
            ),
            FakeResponse(
                json_data={
                    "data": {
                        "matches": [{"id": "2"}],
                    }
                }
            ),
        ]
    )
    client.session = session

    assert client.get_matches_count() == 2
    assert len(session.calls) == 2
