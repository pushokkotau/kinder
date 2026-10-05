from app.services.auto_swipe import AutoSwipeService
from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
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
    def __init__(self, matches=10, events=None):
        self.likes = []
        self.dislikes = []
        self.matches = matches
        self.events = events if events is not None else []

    def set_location(self, latitude, longitude):
        self.events.append(("location", latitude, longitude))

    def get_recommendations(self):
        self.events.append(("recommendations",))
        return []

    def get_matches_count(self):
        self.events.append(("matches", self.matches))
        return self.matches

    def like(self, user_id):
        self.events.append(("like", user_id))
        self.likes.append(user_id)
        self.matches += 1

    def dislike(self, user_id, s_number=None):
        self.events.append(("dislike", user_id, s_number))
        self.dislikes.append((user_id, s_number))


class FakeRecommendationService:
    def __init__(self, batches):
        self.batches = iter(batches)

    def get_batch(self):
        return next(self.batches, [])


class FakeLocation:
    address = "Test City"


class FakeLocationService:
    def __init__(self, client):
        self.client = client

    def set_city(self, city):
        self.client.events.append(("location_service", city))
        self.client.set_location(1.0, 2.0)
        return FakeLocation()


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


def test_auto_swipe_runs_complete_flow_and_calculates_new_matches():
    events = []
    client = FakeTinderClient(matches=10, events=events)
    recommendations = FakeRecommendationService([
        [
            recommendation("like-1", 2),
            recommendation("dislike-1", 1),
        ],
    ])

    service = AutoSwipeService(
        location_service=FakeLocationService(client),
        recommendation_service=recommendations,
        match_service=MatchService(client),
        swipe_service=SwipeService(
            client,
            recommendations,
            swipe_limit=2,
        ),
    )

    result = service.run("Test City")

    assert result.location.address == "Test City"
    assert result.recommendations_received == 2
    assert result.swipe_result.swipes == 2
    assert result.swipe_result.likes == 1
    assert result.swipe_result.dislikes == 1
    assert result.match_stats.before == 10
    assert result.match_stats.after == 11
    assert result.match_stats.new_matches == 1
    assert events == [
        ("location_service", "Test City"),
        ("location", 1.0, 2.0),
        ("matches", 10),
        ("like", "like-1"),
        ("dislike", "dislike-1", 1),
        ("matches", 11),
    ]
