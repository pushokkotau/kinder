from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.auto_swipe import AutoSwipeService
from app.routers.auth import create_auth_router
from app.routers.profile import create_profile_router
from app.routers.recommendations import create_recommendations_router
from app.services.web_auth import WebAuthService
from app.services.web_session import WebSessionStateStore
from app.services.factory import ClientServices, ServiceFactory
from app.services.session import TinderSessionManager
from app.tinder.client import TinderAPIError, TinderClient
from config import get_web_allowed_origins

app = FastAPI(title="Kinder API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_web_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = TinderSessionManager()
web_sessions = WebSessionStateStore()
web_auth = WebAuthService(sessions, web_sessions)
app.include_router(create_auth_router(web_auth))


class LocationRequest(BaseModel):
    city: str = Field(min_length=1)


def get_session_id(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    session_id = authorization.removeprefix("Bearer ").strip()
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return session_id


def remove_web_session(session_id: str) -> None:
    web_auth.remove_session(session_id)


def get_client(authorization: Optional[str] = Header(default=None)) -> TinderClient:
    session_id = get_session_id(authorization)
    try:
        return web_auth.get_authenticated_client(session_id)
    except TinderAPIError as exc:
        detail = str(exc)
        if detail == "Tinder user is not authenticated.":
            detail = "Tinder user is not authenticated"
        else:
            detail = "Invalid session token"
        raise HTTPException(status_code=401, detail=detail) from exc


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}



def get_services(client: TinderClient = Depends(get_client)) -> ClientServices:
    return ServiceFactory.for_client(client)


app.include_router(create_profile_router(get_services))



app.include_router(create_recommendations_router(get_services))

@app.post("/api/v1/swipes/{action}/{user_id}")
def swipe(action: str, user_id: str, services: ClientServices = Depends(get_services)) -> dict[str, str]:
    if action not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Action must be like or dislike")

    if action == "like":
        services.swipe.like(user_id)
    else:
        services.swipe.dislike(user_id)

    return {"action": action, "user_id": user_id}


@app.post("/api/v1/autoswipe")
def autoswipe(
    authorization: Optional[str] = Header(default=None),
    client: TinderClient = Depends(get_client),
) -> dict[str, int | bool]:
    session_id = get_session_id(authorization)
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


@app.get("/api/v1/matches/count")
def matches_count(services: ClientServices = Depends(get_services)) -> dict[str, int]:
    return {"count": services.matches.get_count()}


@app.post("/api/v1/location")
def set_location(
    payload: LocationRequest,
    authorization: Optional[str] = Header(default=None),
    client: TinderClient = Depends(get_client),
) -> dict[str, str | float]:
    services = ServiceFactory.for_client(client)
    location = services.location.set_city(payload.city)
    session_id = get_session_id(authorization)
    web_sessions.set_location(session_id, payload.city, location)
    return {
        "city": payload.city,
        "address": location.address,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }
