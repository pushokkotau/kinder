from typing import Callable, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

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
        authorization: Optional[str] = Header(default=None),
        client: TinderClient = Depends(get_client),
    ) -> dict[str, str | float]:
        services = get_services(client)
        location = services.location.set_city(payload.city)
        session_id = _get_session_id(authorization)
        web_sessions.set_location(session_id, payload.city, location)
        return {
            "city": payload.city,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
        }

    return router


def _get_session_id(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    session_id = authorization.removeprefix("Bearer ").strip()
    if not session_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return session_id
