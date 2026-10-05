# Kinder HTTP API

HTTP API for the web frontend. The Telegram bot remains responsible for AutoSwipe; manual swiping is a frontend feature.

## Endpoints

- GET /api/v1/health
- POST /api/v1/auth/token
- POST /api/v1/auth/phone
- POST /api/v1/auth/phone/verify
- GET /api/v1/profile
- GET /api/v1/recommendations
- POST /api/v1/swipes/like/{user_id}
- POST /api/v1/swipes/dislike/{user_id}
- GET /api/v1/matches/count
- POST /api/v1/location

Authentication uses a short-lived-in-memory Bearer session token for the prototype. Production persistence, expiry, rate limiting and a proper web authentication flow should be added before exposing this API publicly.

The fake Tinder client can be selected with TINDER_API_MODE=fake.
