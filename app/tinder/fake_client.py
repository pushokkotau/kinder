from typing import Optional

from app.tinder.client import TinderAPIError, TinderClient
from app.tinder.models import Profile, Recommendation, TinderUser


class FakeTinderClient(TinderClient):
    """Deterministic Tinder API replacement for local development and tests."""

    TEST_CODE = "1234"
    INITIAL_MATCHES = 10

    def __init__(self) -> None:
        super().__init__(base_url="http://fake-tinder.local")
        self._authenticated = False
        self._matches_count = self.INITIAL_MATCHES
        self._phone: Optional[str] = None
        self._recommendation_index = 0

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def request_auth_phone(self, phone: str) -> None:
        self._phone = phone

    def authenticate_with_phone_code(self, phone: str, code: str) -> str:
        if phone != self._phone or code != self.TEST_CODE:
            raise TinderAPIError("Неверный тестовый код. Используй 1234.")
        self._authenticated = True
        self.set_token("fake-token")
        return "fake-token"

    def authenticate_with_token(self, token: str) -> None:
        if not token:
            raise TinderAPIError("Тестовый token не должен быть пустым.")
        self._authenticated = True
        self.set_token("fake-token")

    def get_profile(self) -> Profile:
        self._require_auth()
        return Profile(
            name="Тестовый пользователь",
            city="Амстердам",
            country="Нидерланды",
        )

    def set_location(self, latitude: float, longitude: float) -> None:
        self._require_auth()
        self._recommendation_index = 0

    def get_recommendations(self) -> list[Recommendation]:
        self._require_auth()

        if self._recommendation_index >= 12:
            return []

        batch = []
        for offset in range(6):
            index = self._recommendation_index + offset
            if index >= 12:
                break

            photos = [{"url": f"https://i.pravatar.cc/800?img={index + 1}"}]
            if index % 2 == 0:
                photos.append({"url": f"https://i.pravatar.cc/800?img={index + 13}"})

            user = TinderUser(
                id=f"fake-user-{index + 1}",
                name=f"Тестовая анкета {index + 1}",
                photos=photos,
                raw={"_id": f"fake-user-{index + 1}"},
            )
            batch.append(
                Recommendation(
                    user=user,
                    s_number=index,
                    raw={"user": user.raw, "s_number": index},
                )
            )

        self._recommendation_index += len(batch)
        return batch

    def like(self, user_id: str) -> None:
        self._require_auth()
        self._matches_count += 1

    def dislike(self, user_id: str, s_number: Optional[int] = None) -> None:
        self._require_auth()

    def get_matches_count(self) -> int:
        self._require_auth()
        return self._matches_count

    def _require_auth(self) -> None:
        if not self._authenticated:
            raise TinderAPIError("Fake Tinder client is not authenticated.")
