from app.tinder.client import TinderClient


class RecommendationService:
    def __init__(self, tinder_client: TinderClient):
        self.client = tinder_client

    def get_batch(self):
        return self.client.get_recommendations()
