from app.services.swipe import SwipeService
from app.tinder.models import MatchStats, Recommendation, TinderUser


def recommendation(user_id: str, photos: int = 2) -> Recommendation:
    return Recommendation(
        user=TinderUser(
            id=user_id,
            name=user_id,
            photos=[{"id": str(i)} for i in range(photos)],
            raw={},
        ),
        s_number=1,
        raw={},
    )


class FakeTinderClient:
    def __init__(self):
        self.likes = []
        self.dislikes = []

    def like(self, user_id):
        self.likes.append(user_id)

    def dislike(self, user_id, s_number=None):
        self.dislikes.append((user_id, s_number))


class FakeRecommendationService:
    def __init__(self, batches):
        self.batches = iter(batches)

    def get_batch(self):
        return next(self.batches, [])


def test_match_stats_calculates_new_matches():
    assert MatchStats(before=10, after=13).new_matches == 3
    assert MatchStats(before=13, after=10).new_matches == 0


def test_swipe_service_likes_profiles_with_two_or_more_photos():
    client = FakeTinderClient()
    service = SwipeService(client, FakeRecommendationService([]), swipe_limit=2)

    result = service.run([
        recommendation("like-1", 2),
        recommendation("like-2", 3),
    ])

    assert result.swipes == 2
    assert result.likes == 2
    assert result.dislikes == 0
    assert client.likes == ["like-1", "like-2"]


def test_swipe_service_dislikes_profiles_with_fewer_than_two_photos():
    client = FakeTinderClient()
    service = SwipeService(client, FakeRecommendationService([]), swipe_limit=2)

    result = service.run([
        recommendation("dislike-1", 1),
        recommendation("like-1", 2),
    ])

    assert result.swipes == 2
    assert result.likes == 1
    assert result.dislikes == 1
    assert client.dislikes == [("dislike-1", 1)]


def test_swipe_service_respects_global_limit():
    client = FakeTinderClient()
    service = SwipeService(client, FakeRecommendationService([]), swipe_limit=1)

    result = service.run([
        recommendation("only-one", 2),
        recommendation("must-not-swipe", 2),
    ])

    assert result.swipes == 1
    assert result.limit_reached is True
    assert client.likes == ["only-one"]
