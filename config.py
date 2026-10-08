# Global application settings.

# Maximum number of Tinder swipes performed by one AutoSwipe run.
SWIPE_LIMIT = 100

# Tinder API mode used for session clients.
import os


def get_tinder_api_mode() -> str:
    return os.getenv("TINDER_API_MODE", "fake").lower()


def get_session_ttl_seconds() -> float:
    return float(os.getenv("SESSION_TTL_SECONDS", "3600"))


def get_web_allowed_origins() -> list[str]:
    value = os.getenv(
        "WEB_ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    )
    return [origin.strip() for origin in value.split(",") if origin.strip()]
