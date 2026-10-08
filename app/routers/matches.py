from typing import Callable

from fastapi import APIRouter, Depends

from app.services.factory import ClientServices


def create_matches_router(
    get_services: Callable[..., ClientServices],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/matches/count")
    def matches_count(
        services: ClientServices = Depends(get_services),
    ) -> dict[str, int]:
        return {"count": services.matches.get_count()}

    return router
