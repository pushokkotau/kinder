from app.tinder.client import TinderClient


class AuthService:
    def __init__(self, tinder_client: TinderClient):
        self.client = tinder_client

    def request_phone_code(self, phone: str) -> None:
        self.client.request_auth_phone(phone)

    def authenticate_with_code(self, phone: str, code: str) -> str:
        return self.client.authenticate_with_phone_code(phone, code)

    def authenticate_with_token(self, token: str) -> None:
        self.client.authenticate_with_token(token)
