from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_session_id
from app.services.factory import ClientServices
from app.services.web_session import WebSessionStateStore


class LocationRequest(BaseModel):
    city: str = Field(min_length=1)

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("City must not be blank")
        return value


def create_location_router(
    get_services: Callable[..., ClientServices],
    web_sessions: WebSessionStateStore,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/location")
    def set_location(
        payload: LocationRequest,
        session_id: str = Depends(get_session_id),
        services: ClientServices = Depends(get_services),
    ) -> dict[str, str | float]:
        try:
            location = services.location.set_city(payload.city)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        web_sessions.set_location(session_id, payload.city, location)
        return {
            "city": payload.city,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
        }

    return router
