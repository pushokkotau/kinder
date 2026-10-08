from typing import Callable, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.services.auto_swipe import AutoSwipeService
from app.services.web_session import WebSessionStateStore
from app.tinder.client import TinderClient


def create_autoswipe_router(
    get_client: Callable[..., TinderClient],
    web_sessions: WebSessionStateStore,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/autoswipe")
    def autoswipe(
        authorization: Optional[str] = Header(default=None),
        client: TinderClient = Depends(get_client),
    ) -> dict[str, int | bool]:
        session_id = _get_session_id(authorization)
        state = web_sessions.get(session_id)
        city = state.city if state else None
        if not city:
            raise HTTPException(
                status_code=400,
                detail="City must be selected before AutoSwipe",
            )

        result = AutoSwipeService.for_client(client).run(
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


def _get_session_id(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    session_id = authorization.removeprefix("Bearer ").strip()
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return session_id
