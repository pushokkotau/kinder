from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.auto_swipe import AutoSwipeService
from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.swipe import SwipeService
from app.services.profile import ProfileService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager
from app.tinder.client import TinderClient
from app.tinder.models import Recommendation

app = FastAPI(title="Kinder API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = TinderSessionManager()
web_session_cities: dict[str, str] = {}
web_phone_sessions: dict[str, str] = {}


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
    sessions.remove(session_id)
    web_session_cities.pop(session_id, None)

    for phone, mapped_session_id in list(web_phone_sessions.items()):
        if mapped_session_id == session_id:
            web_phone_sessions.pop(phone, None)


def get_client(authorization: Optional[str] = Header(default=None)) -> TinderClient:
    session_id = get_session_id(authorization)
    client = sessions.find_client(session_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not client.is_authenticated:
        raise HTTPException(status_code=401, detail="Tinder user is not authenticated")
    return client


def create_web_session() -> tuple[str, TinderClient]:
    session_id = uuid4().hex
    client = sessions.get_client(session_id)
    return session_id, client


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/token")
def authenticate_with_token(payload: TokenAuthRequest) -> dict[str, str]:
    session_id, client = create_web_session()
    try:
        client.authenticate_with_token(payload.token)
    except Exception as exc:
        remove_web_session(session_id)
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"session_token": session_id}


@app.post("/api/v1/auth/phone")
def request_phone_code(payload: PhoneAuthRequest) -> dict[str, object]:
    session_id, client = create_web_session()
    try:
        client.request_auth_phone(payload.phone)
    except Exception as exc:
        remove_web_session(session_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    web_phone_sessions[payload.phone] = session_id
    return {"session_token": session_id, "code_requested": True}


@app.post("/api/v1/auth/phone/verify")
def verify_phone_code(payload: CodeAuthRequest) -> dict[str, str]:
    session_id = web_phone_sessions.get(payload.phone)
    if session_id is None:
        raise HTTPException(status_code=401, detail="Phone authentication session not found")

    client = sessions.find_client(session_id)
    if client is None:
        web_phone_sessions.pop(payload.phone, None)
        raise HTTPException(status_code=401, detail="Phone authentication session not found")

    try:
        token = client.authenticate_with_phone_code(payload.phone, payload.code)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    web_phone_sessions.pop(payload.phone, None)
    return {"session_token": session_id, "tinder_token": token}


@app.post("/api/v1/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
    session_id = get_session_id(authorization)
    if sessions.find_client(session_id) is None:
        raise HTTPException(status_code=401, detail="Invalid session token")

    remove_web_session(session_id)
    return {"status": "logged_out"}


@app.get("/api/v1/profile")
def profile(client: TinderClient = Depends(get_client)) -> dict[str, str]:
    result = ProfileService(client).get_profile()
    return {"name": result.name, "city": result.city, "country": result.country}


def serialize_recommendation(recommendation: Recommendation) -> dict[str, object]:
    return {
        "id": recommendation.user.id,
        "name": recommendation.user.name,
        "photos": recommendation.user.photos,
        "s_number": recommendation.s_number,
    }


@app.get("/api/v1/recommendations")
def recommendations(client: TinderClient = Depends(get_client)) -> dict[str, list[dict[str, object]]]:
    items = RecommendationService(client).get_batch()
    return {"recommendations": [serialize_recommendation(item) for item in items]}


@app.post("/api/v1/swipes/{action}/{user_id}")
def swipe(action: str, user_id: str, client: TinderClient = Depends(get_client)) -> dict[str, str]:
    if action not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Action must be like or dislike")

    if action == "like":
        client.like(user_id)
    else:
        client.dislike(user_id)

    return {"action": action, "user_id": user_id}


@app.post("/api/v1/autoswipe")
def autoswipe(
    authorization: Optional[str] = Header(default=None),
    client: TinderClient = Depends(get_client),
) -> dict[str, int | bool]:
    session_id = get_session_id(authorization)
    city = web_session_cities.get(session_id)
    if not city:
        raise HTTPException(
            status_code=400,
            detail="City must be selected before AutoSwipe",
        )

    recommendations = RecommendationService(client)
    result = AutoSwipeService(
        location_service=LocationService(client),
        recommendation_service=recommendations,
        match_service=MatchService(client),
        swipe_service=SwipeService(client, recommendations),
    ).run(city)

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
def matches_count(client: TinderClient = Depends(get_client)) -> dict[str, int]:
    return {"count": MatchService(client).get_count()}


@app.post("/api/v1/location")
def set_location(
    payload: LocationRequest,
    authorization: Optional[str] = Header(default=None),
    client: TinderClient = Depends(get_client),
) -> dict[str, str | float]:
    location = LocationService(client).set_city(payload.city)
    session_id = get_session_id(authorization)
    web_session_cities[session_id] = payload.city
    return {
        "city": payload.city,
        "address": location.address,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }
