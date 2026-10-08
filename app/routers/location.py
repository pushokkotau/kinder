from typing import Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_session_id
from app.services.factory import ClientServices
from app.services.web_session import WebSessionStateStore
from app.tinder.client import TinderClient


class LocationRequest(BaseModel):
    city: str = Field(min_length=1)


def create_location_router(
    get_client: Callable[..., TinderClient],
    get_services: Callable[..., ClientServices],
    web_sessions: WebSessionStateStore,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/location")
    def set_location(
        payload: LocationRequest,
        session_id: str = Depends(get_session_id),
        client: TinderClient = Depends(get_client),
    ) -> dict[str, str | float]:
        services = get_services(client)
        location = services.location.set_city(payload.city)
        web_sessions.set_location(session_id, payload.city, location)
        return {
            "city": payload.city,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
        }

    return router
