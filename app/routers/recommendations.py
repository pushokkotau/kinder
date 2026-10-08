from typing import Callable

from fastapi import APIRouter, Depends

from app.services.factory import ClientServices
from app.tinder.models import Recommendation


def create_recommendations_router(
    get_services: Callable[..., ClientServices],
) -> APIRouter:
    router = APIRouter()

    def serialize_recommendation(
        recommendation: Recommendation,
    ) -> dict[str, object]:
        return {
            "id": recommendation.user.id,
            "name": recommendation.user.name,
            "photos": recommendation.user.photos,
            "s_number": recommendation.s_number,
        }

    @router.get("/api/v1/recommendations")
    def recommendations(
        services: ClientServices = Depends(get_services),
    ) -> dict[str, list[dict[str, object]]]:
        items = services.recommendations.get_batch()
        return {
            "recommendations": [
                serialize_recommendation(item) for item in items
            ]
        }

    return router
