from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.location import LocationService
from app.services.swipe import SwipeService
from app.services.matches import MatchService
from app.services.profile import ProfileService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager

app = FastAPI(title="Kinder API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = TinderSessionManager()
web_sessions: dict[str, object] = {}


class TokenAuthRequest(BaseModel):
    token: str = Field(min_length=1)


class PhoneAuthRequest(BaseModel):
    phone: str = Field(min_length=1)


class CodeAuthRequest(BaseModel):
    phone: str = Field(min_length=1)
    code: str = Field(min_length=1)


class LocationRequest(BaseModel):
    city: str = Field(min_length=1)


def get_client(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    session_id = authorization.removeprefix("Bearer ").strip()
    client = web_sessions.get(session_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not client.is_authenticated:
        raise HTTPException(status_code=401, detail="Tinder user is not authenticated")
    return client


def create_web_session() -> tuple[str, object]:
    session_id = uuid4().hex
    client = sessions.get_client(session_id)
    web_sessions[session_id] = client
    return session_id, client


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/token")
def authenticate_with_token(payload: TokenAuthRequest):
    session_id, client = create_web_session()
    try:
        client.authenticate_with_token(payload.token)
    except Exception as exc:
        web_sessions.pop(session_id, None)
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"session_token": session_id}


@app.post("/api/v1/auth/phone")
def request_phone_code(payload: PhoneAuthRequest):
    session_id, client = create_web_session()
    try:
        client.request_auth_phone(payload.phone)
    except Exception as exc:
        web_sessions.pop(session_id, None)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_token": session_id, "code_requested": True}


@app.post("/api/v1/auth/phone/verify")
def verify_phone_code(payload: CodeAuthRequest):
    for session_id, client in web_sessions.items():
        if getattr(client, "_phone", None) == payload.phone:
            try:
                token = client.authenticate_with_phone_code(payload.phone, payload.code)
            except Exception as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
            return {"session_token": session_id, "tinder_token": token}
    raise HTTPException(status_code=401, detail="Phone authentication session not found")


@app.get("/api/v1/profile")
def profile(client=Depends(get_client)):
    result = ProfileService(client).get_profile()
    return {"name": result.name, "city": result.city, "country": result.country}


def serialize_recommendation(recommendation):
    return {
        "id": recommendation.user.id,
        "name": recommendation.user.name,
        "photos": recommendation.user.photos,
        "s_number": recommendation.s_number,
    }


@app.get("/api/v1/recommendations")
def recommendations(client=Depends(get_client)):
    items = RecommendationService(client).get_batch()
    return {"recommendations": [serialize_recommendation(item) for item in items]}


@app.post("/api/v1/swipes/{action}/{user_id}")
def swipe(action: str, user_id: str, client=Depends(get_client)):
    if action not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Action must be like or dislike")

    if action == "like":
        client.like(user_id)
    else:
        client.dislike(user_id)

    return {"action": action, "user_id": user_id}


@app.post("/api/v1/autoswipe")
def autoswipe(client=Depends(get_client)):
    before = MatchService(client).snapshot()
    recommendations = RecommendationService(client).get_batch()
    result = SwipeService(client, RecommendationService(client)).run(recommendations)
    after = MatchService(client).snapshot()
    stats = MatchService(client).calculate(before, after)
    return {
        "swipes": result.swipes,
        "likes": result.likes,
        "dislikes": result.dislikes,
        "limit_reached": result.limit_reached,
        "recommendations_exhausted": result.recommendations_exhausted,
        "recommendations_received": result.recommendations_received,
        "matches_before": stats.before,
        "matches_after": stats.after,
        "new_matches": stats.new_matches,
    }


@app.get("/api/v1/matches/count")
def matches_count(client=Depends(get_client)):
    return {"count": MatchService(client).get_count()}


@app.post("/api/v1/location")
def set_location(payload: LocationRequest, client=Depends(get_client)):
    location = LocationService(client).set_city(payload.city)
    return {
        "city": payload.city,
        "address": location.address,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }
