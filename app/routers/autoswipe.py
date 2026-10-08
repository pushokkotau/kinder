from typing import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_session_id
from app.services.factory import ClientServices
from app.services.web_session import WebSessionStateStore


def create_autoswipe_router(
    get_services: Callable[..., ClientServices],
    web_sessions: WebSessionStateStore,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/autoswipe")
    def autoswipe(
        session_id: str = Depends(get_session_id),
        services: ClientServices = Depends(get_services),
    ) -> dict[str, int | bool]:
        state = web_sessions.get(session_id)
        city = state.city if state else None
        if not city:
            raise HTTPException(
                status_code=400,
                detail="City must be selected before AutoSwipe",
            )

        result = services.autoswipe.run(
            city,
            resolved_location=state.location if state else None,
        )

        return {
            "swipes": result.swipe_result.swipes,
            "likes": result.swipe_result.likes,
            "dislikes": result.swipe_result.dislikes,
            "limit_reached": result.swipe_result.limit_reached,
            "recommendations_exhausted": result.swipe_result.recommendations_exhausted,
            "recommendations_received": result.recommendations_received,
            "matches_before": result.match_stats.before,
            "matches_after": result.match_stats.after,
            "new_matches": result.match_stats.new_matches,
        }

    return router
