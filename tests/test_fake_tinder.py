from app.tinder.fake_client import FakeTinderClient


def test_fake_phone_authentication_uses_fixed_code():
    client = FakeTinderClient()

    client.request_auth_phone("+31612345678")
    client.authenticate_with_phone_code("+31612345678", "1234")

    assert client.is_authenticated
    assert client.get_profile().name == "Тестовый пользователь"


def test_fake_matches_increase_after_likes():
    client = FakeTinderClient()
    client.authenticate_with_token("test-token")

    assert client.get_matches_count() == 10

    recommendations = client.get_recommendations()
    for recommendation in recommendations:
        if len(recommendation.user.photos) >= 2:
            client.like(recommendation.user.id)

    assert client.get_matches_count() == 13


def test_fake_recommendations_are_finite_and_deterministic():
    client = FakeTinderClient()
    client.authenticate_with_token("test-token")

    first_batch = client.get_recommendations()
    second_batch = client.get_recommendations()
    third_batch = client.get_recommendations()

    assert len(first_batch) == 6
    assert len(second_batch) == 6
    assert third_batch == []
    assert first_batch[0].user.id == "fake-user-1"
    assert second_batch[0].user.id == "fake-user-7"
