from app.services.auto_swipe import AutoSwipeService
from app.tinder.models import MatchStats, SwipeResult


class FakeLocationService:
    def __init__(self, events):
        self.events = events

    def set_city(self, city):
        self.events.append(("location", city))
        return {"address": city}


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
    assert result.recommendations_received == 1
    assert result.match_stats.before == 10
    assert result.match_stats.after == 12
    assert result.match_stats.new_matches == 2


def test_auto_swipe_reports_recommendations_from_all_batches():
    events = []
    recommendations = FakeRecommendations(
        events,
        batches=[["first"], ["second", "third"]],
    )
    swipes = FakeSwipes(events, recommendations_received=3)
    service = AutoSwipeService(
        location_service=FakeLocationService(events),
        recommendation_service=recommendations,
        match_service=FakeMatches(events),
        swipe_service=swipes,
    )

    result = service.run("Amsterdam")

    assert result.recommendations_received == 3


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
