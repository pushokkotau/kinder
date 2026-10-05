from app.services.auto_swipe import AutoSwipeService
from app.tinder.models import MatchStats, SwipeResult


class FakeLocationService:
    def __init__(self, events):
        self.events = events

    def set_city(self, city):
        self.events.append(("location", city))
        return {"address": city}


class FakeRecommendations:
    def __init__(self, events):
        self.events = events

    def get_batch(self):
        self.events.append("recommendations")
        return ["recommendation"]


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
    def __init__(self, events):
        self.events = events

    def run(self, batch):
        self.events.append(("swipes", batch))
        return SwipeResult(
            swipes=1,
            likes=1,
            dislikes=0,
            limit_reached=False,
            recommendations_exhausted=True,
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
