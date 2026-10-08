from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.routers.autoswipe import create_autoswipe_router
from app.routers.auth import create_auth_router
from app.routers.location import create_location_router
from app.routers.profile import create_profile_router
from app.routers.recommendations import create_recommendations_router
from app.routers.swipe import create_swipe_router
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


app.include_router(create_swipe_router(get_services))


app.include_router(create_autoswipe_router(get_client, web_sessions))

@app.get("/api/v1/matches/count")
def matches_count(services: ClientServices = Depends(get_services)) -> dict[str, int]:
    return {"count": services.matches.get_count()}



app.include_router(create_location_router(get_client, get_services, web_sessions))
