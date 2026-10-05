from app.services.swipe import SwipeService
from app.tinder.models import Recommendation, TinderUser


def recommendation(user_id, photos, s_number=1):
    user = TinderUser(
        id=user_id,
        name=user_id,
        photos=photos,
        raw={"_id": user_id},
    )
    return Recommendation(user=user, s_number=s_number, raw={})


class FakeSwipeClient:
    def __init__(self):
        self.likes = []
        self.dislikes = []

    def like(self, user_id):
        self.likes.append(user_id)

    def dislike(self, user_id, s_number=None):
        self.dislikes.append((user_id, s_number))


class FakeRecommendations:
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = 0

    def get_batch(self):
        self.calls += 1
        if not self.batches:
            return []
        return self.batches.pop(0)


def test_two_or_more_photos_are_liked_and_single_photo_is_disliked():
    client = FakeSwipeClient()
    recommendations = FakeRecommendations([])
    service = SwipeService(client, recommendations, swipe_limit=10)

    result = service.run([
        recommendation("one", [{"url": "1"}]),
        recommendation("two", [{"url": "1"}, {"url": "2"}]),
        recommendation("three", [{"url": "1"}, {"url": "2"}, {"url": "3"}]),
    ])

    assert result.swipes == 3
    assert result.likes == 2
    assert result.dislikes == 1
    assert result.recommendations_exhausted is True
    assert result.limit_reached is False
    assert client.likes == ["two", "three"]
    assert client.dislikes == [("one", 1)]


def test_swipe_limit_stops_processing_remaining_recommendations():
    client = FakeSwipeClient()
    recommendations = FakeRecommendations([])
    service = SwipeService(client, recommendations, swipe_limit=2)

    result = service.run([
        recommendation("one", [{"url": "1"}]),
        recommendation("two", [{"url": "1"}, {"url": "2"}]),
        recommendation("three", [{"url": "1"}, {"url": "2"}]),
    ])

    assert result.swipes == 2
    assert result.likes == 1
    assert result.dislikes == 1
    assert result.limit_reached is True
    assert result.recommendations_exhausted is False


def test_duplicate_recommendations_are_swiped_only_once():
    client = FakeSwipeClient()
    recommendations = FakeRecommendations([])
    service = SwipeService(client, recommendations, swipe_limit=10)

    result = service.run([
        recommendation("same", [{"url": "1"}, {"url": "2"}]),
        recommendation("same", [{"url": "1"}, {"url": "2"}]),
    ])

    assert result.swipes == 1
    assert result.likes == 1
    assert result.dislikes == 0
    assert client.likes == ["same"]


def test_service_fetches_next_batch_until_limit_or_exhaustion():
    client = FakeSwipeClient()
    recommendations = FakeRecommendations([
        [recommendation("two", [{"url": "1"}, {"url": "2"}])],
        [recommendation("three", [{"url": "1"}])],
    ])
    service = SwipeService(client, recommendations, swipe_limit=3)

    result = service.run([recommendation("one", [{"url": "1"}])])

    assert result.swipes == 3
    assert result.likes == 1
    assert result.dislikes == 2
    assert result.limit_reached is True
    assert result.recommendations_exhausted is False
    assert recommendations.calls == 2
