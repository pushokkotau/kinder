from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TinderUser:
    id: str
    name: str
    photos: list[dict[str, Any]]
    raw: dict[str, Any]


@dataclass(frozen=True)
class Recommendation:
    user: TinderUser
    s_number: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class Profile:
    name: str
    city: str
    country: str


@dataclass(frozen=True)
class SwipeResult:
    swipes: int
    likes: int
    dislikes: int
    limit_reached: bool
    recommendations_exhausted: bool
    recommendations_received: int


@dataclass(frozen=True)
class MatchStats:
    before: int
    after: int

    @property
    def new_matches(self) -> int:
        return max(0, self.after - self.before)
