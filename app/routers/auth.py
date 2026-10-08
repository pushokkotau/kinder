from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.web_auth import WebAuthService
from app.tinder.client import TinderAPIError


class TokenAuthRequest(BaseModel):
    token: str = Field(min_length=1)


class PhoneAuthRequest(BaseModel):
    phone: str = Field(min_length=1)


class CodeAuthRequest(BaseModel):
    phone: str = Field(min_length=1)
    code: str = Field(min_length=1)


def _get_session_id(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    session_id = authorization.removeprefix("Bearer ").strip()
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return session_id


def create_auth_router(web_auth: WebAuthService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth")

    @router.post("/token")
    def authenticate_with_token(payload: TokenAuthRequest) -> dict[str, str]:
        try:
            session_id = web_auth.authenticate_with_token(payload.token)
        except (TinderAPIError, ValueError) as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"session_token": session_id}

    @router.post("/phone")
    def request_phone_code(payload: PhoneAuthRequest) -> dict[str, object]:
        try:
            session_id = web_auth.request_phone_code(payload.phone)
        except (TinderAPIError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session_token": session_id, "code_requested": True}

    @router.post("/phone/verify")
    def verify_phone_code(payload: CodeAuthRequest) -> dict[str, str]:
        try:
            session_id, token = web_auth.verify_phone_code(payload.phone, payload.code)
        except (TinderAPIError, ValueError) as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"session_token": session_id, "tinder_token": token}

    @router.post("/logout")
    def logout(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
        session_id = _get_session_id(authorization)
        try:
            web_auth.logout(session_id)
        except TinderAPIError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"status": "logged_out"}

    return router
