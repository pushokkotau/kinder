from typing import Callable

from fastapi import APIRouter, Depends

from app.services.factory import ClientServices


def create_profile_router(
    get_services: Callable[..., ClientServices],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/profile")
    def profile(
        services: ClientServices = Depends(get_services),
    ) -> dict[str, str]:
        result = services.profile.get_profile()
        return {
            "name": result.name,
            "city": result.city,
            "country": result.country,
        }

    return router
