from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.auto_swipe import AutoSwipeService
from app.services.web_auth import WebAuthService
from app.services.web_session import WebSessionStateStore
from app.services.factory import ClientServices, ServiceFactory
from app.services.session import TinderSessionManager
from app.tinder.client import TinderAPIError, TinderClient
from app.tinder.models import Recommendation
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


class TokenAuthRequest(BaseModel):
    token: str = Field(min_length=1)


class PhoneAuthRequest(BaseModel):
    phone: str = Field(min_length=1)


class CodeAuthRequest(BaseModel):
    phone: str = Field(min_length=1)
    code: str = Field(min_length=1)


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


@app.post("/api/v1/auth/token")
def authenticate_with_token(payload: TokenAuthRequest) -> dict[str, str]:
    try:
        session_id = web_auth.authenticate_with_token(payload.token)
    except (TinderAPIError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"session_token": session_id}


@app.post("/api/v1/auth/phone")
def request_phone_code(payload: PhoneAuthRequest) -> dict[str, object]:
    try:
        session_id = web_auth.request_phone_code(payload.phone)
    except (TinderAPIError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_token": session_id, "code_requested": True}


@app.post("/api/v1/auth/phone/verify")
def verify_phone_code(payload: CodeAuthRequest) -> dict[str, str]:
    try:
        session_id, token = web_auth.verify_phone_code(payload.phone, payload.code)
    except (TinderAPIError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"session_token": session_id, "tinder_token": token}


@app.post("/api/v1/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
    session_id = get_session_id(authorization)
    try:
        web_auth.logout(session_id)
    except TinderAPIError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"status": "logged_out"}


def get_services(client: TinderClient = Depends(get_client)) -> ClientServices:
    return ServiceFactory.for_client(client)


@app.get("/api/v1/profile")
def profile(services: ClientServices = Depends(get_services)) -> dict[str, str]:
    result = services.profile.get_profile()
    return {"name": result.name, "city": result.city, "country": result.country}


def serialize_recommendation(recommendation: Recommendation) -> dict[str, object]:
    return {
        "id": recommendation.user.id,
        "name": recommendation.user.name,
        "photos": recommendation.user.photos,
        "s_number": recommendation.s_number,
    }


@app.get("/api/v1/recommendations")
def recommendations(services: ClientServices = Depends(get_services)) -> dict[str, list[dict[str, object]]]:
    items = services.recommendations.get_batch()
    return {"recommendations": [serialize_recommendation(item) for item in items]}


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
