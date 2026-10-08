from app.services.swipe import SwipeService
from app.tinder.models import Recommendation, TinderUser


def recommendation(user_id, photos, s_number=1):
    user = TinderUser(id=user_id, name=user_id, photos=photos, raw={"_id": user_id})
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
    service = SwipeService(client, FakeRecommendations([]), swipe_limit=10)

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
    assert result.recommendations_received == 3
    assert client.likes == ["two", "three"]
    assert client.dislikes == [("one", 1)]


def test_swipe_limit_stops_processing_remaining_recommendations():
    client = FakeSwipeClient()
    service = SwipeService(client, FakeRecommendations([]), swipe_limit=2)

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
    assert result.recommendations_received == 3


def test_duplicate_recommendations_are_swiped_only_once():
    client = FakeSwipeClient()
    service = SwipeService(client, FakeRecommendations([]), swipe_limit=10)

    result = service.run([
        recommendation("same", [{"url": "1"}, {"url": "2"}]),
        recommendation("same", [{"url": "1"}, {"url": "2"}]),
    ])

    assert result.swipes == 1
    assert result.likes == 1
    assert result.dislikes == 0
    assert result.recommendations_received == 2
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
    assert result.recommendations_received == 3
    assert recommendations.calls == 2


def test_zero_swipe_limit_performs_no_swipes():
    client = FakeSwipeClient()
    service = SwipeService(client, FakeRecommendations([]), swipe_limit=0)

    result = service.run([recommendation("one", [{"url": "1"}])])

    assert result.swipes == 0
    assert result.likes == 0
    assert result.dislikes == 0
    assert result.recommendations_received == 0
    assert result.limit_reached is True
    assert client.likes == []
    assert client.dislikes == []


def test_empty_next_batch_marks_recommendations_exhausted():
    client = FakeSwipeClient()
    recommendations = FakeRecommendations([[]])
    service = SwipeService(client, recommendations, swipe_limit=10)

    result = service.run([recommendation("one", [{"url": "1"}])])

    assert result.swipes == 1
    assert result.recommendations_received == 1
    assert result.recommendations_exhausted is True
    assert result.limit_reached is False
    assert recommendations.calls == 1


def test_api_error_is_not_counted_as_successful_swipe():
    class FailingClient(FakeSwipeClient):
        def like(self, user_id):
            raise RuntimeError("Tinder API failed")

    client = FailingClient()
    service = SwipeService(client, FakeRecommendations([]), swipe_limit=10)

    try:
        service.run([recommendation("one", [{"url": "1"}, {"url": "2"}])])
    except RuntimeError as exc:
        assert str(exc) == "Tinder API failed"
    else:
        raise AssertionError("Expected Tinder API error")

    assert client.likes == []


def test_single_like_is_delegated_to_client():
    client = FakeSwipeClient()
    service = SwipeService(client, FakeRecommendations([]))

    service.like("user-1")

    assert client.likes == ["user-1"]


def test_single_dislike_is_delegated_to_client():
    client = FakeSwipeClient()
    service = SwipeService(client, FakeRecommendations([]))

    service.dislike("user-1", 7)

    assert client.dislikes == [("user-1", 7)]
