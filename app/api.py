from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.dependencies import get_session_id
from app.routers.autoswipe import create_autoswipe_router
from app.routers.auth import create_auth_router
from app.routers.location import create_location_router
from app.routers.matches import create_matches_router
from app.routers.profile import create_profile_router
from app.routers.recommendations import create_recommendations_router
from app.routers.swipe import create_swipe_router
from app.services.factory import ClientServices, ServiceFactory
from app.services.web_auth import WebAuthService
from app.services.web_session import WebSessionStateStore
from app.services.session import TinderSessionManager
from app.tinder.client import TinderAPIError, TinderClient
from config import get_web_allowed_origins

app = FastAPI(title="Kinder API", version="1.0.0")

@app.exception_handler(TinderAPIError)
async def tinder_api_error_handler(request: Request, exc: TinderAPIError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "Tinder API request failed"})


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


def remove_web_session(session_id: str) -> None:
    web_auth.remove_session(session_id)


def get_client(session_id: str = Depends(get_session_id)) -> TinderClient:
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
app.include_router(create_autoswipe_router(get_services, web_sessions))
app.include_router(create_matches_router(get_services))
app.include_router(create_location_router(get_services, web_sessions))
