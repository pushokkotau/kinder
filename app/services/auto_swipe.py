from dataclasses import dataclass
from typing import Any

from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
from app.services.swipe import SwipeService
from app.tinder.client import TinderClient
from app.tinder.models import MatchStats, SwipeResult


@dataclass(frozen=True)
class AutoSwipeResult:
    swipe_result: SwipeResult
    match_stats: MatchStats
    recommendations_received: int
    location: Any


class AutoSwipeService:
    """Orchestrates one complete AutoSwipe run."""

    def __init__(
        self,
        location_service: LocationService,
        recommendation_service: RecommendationService,
        match_service: MatchService,
        swipe_service: SwipeService,
    ):
        self.location_service = location_service
        self.recommendations = recommendation_service
        self.matches = match_service
        self.swipes = swipe_service

    @classmethod
    def for_client(cls, client: TinderClient) -> "AutoSwipeService":
        recommendations = RecommendationService(client)
        return cls(
            location_service=LocationService(client),
            recommendation_service=recommendations,
            match_service=MatchService(client),
            swipe_service=SwipeService(client, recommendations),
        )

    def run(self, city: str, resolved_location: Any = None) -> AutoSwipeResult:
        location = (
            self.location_service.set_location(resolved_location)
            if resolved_location is not None
            else self.location_service.set_city(city)
        )

        # Fetch recommendations before taking the match snapshot and before
        # performing any swipe, as required by the AutoSwipe flow.
        first_batch = self.recommendations.get_batch()
        before = self.matches.snapshot()

        # Do not ask the recommendation API for the same empty batch again.
        if not first_batch:
            swipe_result = SwipeResult(
                swipes=0,
                likes=0,
                dislikes=0,
                limit_reached=False,
                recommendations_exhausted=True,
                recommendations_received=0,
            )
        else:
            swipe_result = self.swipes.run(first_batch)

        after = self.matches.snapshot()
        match_stats = self.matches.calculate(before, after)

        return AutoSwipeResult(
            swipe_result=swipe_result,
            match_stats=match_stats,
            recommendations_received=swipe_result.recommendations_received,
            location=location,
        )
