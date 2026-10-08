# Global application settings.

# Maximum number of Tinder swipes performed by one AutoSwipe run.
SWIPE_LIMIT = 100

# Tinder API mode used for session clients.
import os


def get_tinder_api_mode() -> str:
    return os.getenv("TINDER_API_MODE", "fake").lower()


def get_session_ttl_seconds() -> float:
    return float(os.getenv("SESSION_TTL_SECONDS", "3600"))
