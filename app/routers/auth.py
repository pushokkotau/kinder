from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_session_id
from app.services.web_auth import WebAuthService
from app.tinder.client import TinderAPIError


def _require_non_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value must not be blank")
    return value


class TokenAuthRequest(BaseModel):
    token: str = Field(min_length=1)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        return _require_non_blank(value)


class PhoneAuthRequest(BaseModel):
    phone: str = Field(min_length=1)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return _require_non_blank(value)


class CodeAuthRequest(BaseModel):
    phone: str = Field(min_length=1)
    code: str = Field(min_length=1)

    @field_validator("phone", "code")
    @classmethod
    def validate_value(cls, value: str) -> str:
        return _require_non_blank(value)


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
    def logout(session_id: str = Depends(get_session_id)) -> dict[str, str]:
        try:
            web_auth.logout(session_id)
        except TinderAPIError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"status": "logged_out"}

    return router
