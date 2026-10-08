from app.tinder.client import TinderClient


class ProfileService:
    def __init__(self, tinder_client: TinderClient):
        self.client = tinder_client

    def get_profile(self):
        return self.client.get_profile()
