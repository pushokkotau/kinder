from dataclasses import dataclass

from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.profile import ProfileService
from app.services.recommendations import RecommendationService
from app.services.swipe import SwipeService
from app.tinder.client import TinderClient


@dataclass(frozen=True)
class ClientServices:
    """Service graph composed around one authenticated Tinder client."""

    profile: ProfileService
    recommendations: RecommendationService
    swipe: SwipeService
    location: LocationService
    matches: MatchService


class ServiceFactory:
    """Builds the application services that share one Tinder client."""

    @staticmethod
    def for_client(client: TinderClient) -> ClientServices:
        recommendations = RecommendationService(client)
        return ClientServices(
            profile=ProfileService(client),
            recommendations=recommendations,
            swipe=SwipeService(client, recommendations),
            location=LocationService(client),
            matches=MatchService(client),
        )
