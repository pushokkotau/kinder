from typing import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.services.factory import ClientServices


def create_swipe_router(
    get_services: Callable[..., ClientServices],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/swipes/{action}/{user_id}")
    def swipe(
        action: str,
        user_id: str,
        services: ClientServices = Depends(get_services),
    ) -> dict[str, str]:
        if action not in {"like", "dislike"}:
            raise HTTPException(
                status_code=400,
                detail="Action must be like or dislike",
            )

        if action == "like":
            services.swipe.like(user_id)
        else:
            services.swipe.dislike(user_id)

        return {"action": action, "user_id": user_id}

    return router
