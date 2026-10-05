from app.services.matches import MatchService


class FakeMatchesClient:
    def __init__(self, count=10):
        self.count = count

    def get_matches_count(self):
        return self.count


def test_snapshot_reads_current_match_count():
    client = FakeMatchesClient(10)
    service = MatchService(client)

    assert service.snapshot() == 10

    client.count = 14
    assert service.snapshot() == 14


def test_calculate_returns_new_match_delta():
    service = MatchService(FakeMatchesClient())

    stats = service.calculate(10, 13)

    assert stats.before == 10
    assert stats.after == 13
    assert stats.new_matches == 3


def test_new_matches_never_goes_below_zero():
    service = MatchService(FakeMatchesClient())

    stats = service.calculate(13, 10)

    assert stats.new_matches == 0
