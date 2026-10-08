# Kinder HTTP API

HTTP API for clients of the Kinder backend.

The API shares the same application services as the Telegram bot. AutoSwipe is intentionally exposed through the API as well, so a future web client can use the same AutoSwipe business logic without duplicating it.

## Endpoints

- GET /api/v1/health
- POST /api/v1/auth/token
- POST /api/v1/auth/phone
- POST /api/v1/auth/phone/verify
- POST /api/v1/auth/logout
- GET /api/v1/profile
- GET /api/v1/recommendations
- POST /api/v1/swipes/like/{user_id}
- POST /api/v1/swipes/dislike/{user_id}
- POST /api/v1/autoswipe
- GET /api/v1/matches/count
- POST /api/v1/location

Authentication uses a short-lived in-memory Bearer session token. Production persistence, expiry, rate limiting, and a production-ready authentication flow should be added before exposing this API publicly.

The fake Tinder client can be selected with `TINDER_API_MODE=fake`.

The HTTP API does not contain separate AutoSwipe business logic. The `/api/v1/autoswipe` endpoint delegates to the shared `AutoSwipeService`, which is also used by the Telegram bot.
