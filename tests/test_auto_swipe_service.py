from app.services.auto_swipe import AutoSwipeService
from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
from app.services.swipe import SwipeService
from app.tinder.models import (
    Location,
    MatchStats,
    Recommendation,
    SwipeResult,
    TinderUser,
)


class FakeLocationService:
    def __init__(self, events):
        self.events = events

    def set_city(self, city):
        self.events.append(("location", city))
        return Location(latitude=52.37, longitude=4.90, address=city)


class FakeRecommendations:
    def __init__(self, events, batches=None):
        self.events = events
        self.batches = [["recommendation"]] if batches is None else list(batches)
        self.calls = 0

    def get_batch(self):
        self.calls += 1
        self.events.append("recommendations")
        if not self.batches:
            return []
        return self.batches.pop(0)


class FakeMatches:
    def __init__(self, events):
        self.events = events
        self.counts = iter([10, 12])

    def snapshot(self):
        value = next(self.counts)
        self.events.append(("matches", value))
        return value

    def calculate(self, before, after):
        self.events.append(("calculate", before, after))
        return MatchStats(before=before, after=after)


class FakeSwipes:
    def __init__(self, events, recommendations_received=1):
        self.events = events
        self.calls = 0
        self.recommendations_received = recommendations_received

    def run(self, batch):
        self.calls += 1
        self.events.append(("swipes", batch))
        return SwipeResult(
            swipes=1,
            likes=1,
            dislikes=0,
            limit_reached=False,
            recommendations_exhausted=True,
            recommendations_received=self.recommendations_received,
        )


def recommendation(user_id, photos):
    user = TinderUser(
        id=user_id,
        name=user_id,
        photos=photos,
        raw={"_id": user_id},
    )
    return Recommendation(user=user, s_number=1, raw={})


class FakeAutoSwipeClient:
    def __init__(self, batches):
        self.batches = list(batches)
        self.recommendation_calls = 0
        self.match_count = 10
        self.likes = []
        self.dislikes = []

    def set_location(self, latitude, longitude):
        pass

    def get_recommendations(self):
        self.recommendation_calls += 1
        if not self.batches:
            return []
        return self.batches.pop(0)

    def get_matches_count(self):
        return self.match_count

    def like(self, user_id):
        self.likes.append(user_id)
        self.match_count += 1

    def dislike(self, user_id, s_number=None):
        self.dislikes.append((user_id, s_number))


def test_auto_swipe_follows_required_business_order():
    events = []
    service = AutoSwipeService(
        location_service=FakeLocationService(events),
        recommendation_service=FakeRecommendations(events),
        match_service=FakeMatches(events),
        swipe_service=FakeSwipes(events),
    )

    result = service.run("Amsterdam")

    assert events == [
        ("location", "Amsterdam"),
        "recommendations",
        ("matches", 10),
        ("swipes", ["recommendation"]),
        ("matches", 12),
        ("calculate", 10, 12),
    ]
    assert result.location == Location(
        latitude=52.37,
        longitude=4.90,
        address="Amsterdam",
    )
    assert result.recommendations_received == 1
    assert result.match_stats.before == 10
    assert result.match_stats.after == 12
    assert result.match_stats.new_matches == 2


def test_auto_swipe_reuses_resolved_location_without_resetting_it():
    events = []
    service = AutoSwipeService(
        location_service=FakeLocationService(events),
        recommendation_service=FakeRecommendations(events),
        match_service=FakeMatches(events),
        swipe_service=FakeSwipes(events),
    )

    resolved_location = Location(
        latitude=52.37,
        longitude=4.90,
        address="Amsterdam",
    )

    result = service.run("Amsterdam", resolved_location=resolved_location)

    assert result.location is resolved_location
    assert ("location", "Amsterdam") not in events
    assert events == [
        "recommendations",
        ("matches", 10),
        ("swipes", ["recommendation"]),
        ("matches", 12),
        ("calculate", 10, 12),
    ]


def test_auto_swipe_processes_multiple_recommendation_batches_until_limit():
    client = FakeAutoSwipeClient(
        batches=[
            [
                recommendation("first", [{"url": "1"}]),
                recommendation("second", [{"url": "1"}]),
            ],
            [
                recommendation("third", [{"url": "1"}, {"url": "2"}]),
                recommendation("fourth", [{"url": "1"}]),
            ],
        ]
    )
    recommendations = RecommendationService(client)
    service = AutoSwipeService(
        location_service=FakeLocationService([]),
        recommendation_service=recommendations,
        match_service=MatchService(client),
        swipe_service=SwipeService(client, recommendations, swipe_limit=3),
    )

    result = service.run("Amsterdam")

    assert client.recommendation_calls == 2
    assert client.likes == ["third"]
    assert client.dislikes == [("first", 1), ("second", 1)]
    assert result.recommendations_received == 4
    assert result.swipe_result.swipes == 3
    assert result.swipe_result.limit_reached is True
    assert result.swipe_result.recommendations_exhausted is False
    assert result.match_stats.before == 10
    assert result.match_stats.after == 11
    assert result.match_stats.new_matches == 1


def test_empty_first_batch_does_not_fetch_recommendations_twice():
    events = []
    recommendations = FakeRecommendations(events, batches=[[]])
    swipes = FakeSwipes(events)
    service = AutoSwipeService(
        location_service=FakeLocationService(events),
        recommendation_service=recommendations,
        match_service=FakeMatches(events),
        swipe_service=swipes,
    )

    result = service.run("Amsterdam")

    assert recommendations.calls == 1
    assert swipes.calls == 0
    assert result.recommendations_received == 0
    assert result.swipe_result.swipes == 0
    assert result.swipe_result.recommendations_exhausted is True
    assert result.match_stats.before == 10
    assert result.match_stats.after == 12
