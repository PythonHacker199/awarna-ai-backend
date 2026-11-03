"""Only signed-in Awarna users may use the AI service.

The apps send the user's Supabase access token as `Authorization: Bearer …`.
We ask Supabase who the token belongs to (so no JWT secret lives here),
remember the answer for a few minutes, and cap how many documents one user
can send in a window so nobody can run up the AI bill.
"""

import hashlib
import logging
import time
from collections import deque

import httpx
from fastapi import Header, HTTPException

from .config import settings


logger = logging.getLogger("awarna.auth")

# sha256(token) -> (user id, monotonic expiry). Tokens themselves are never kept.
_verified: dict[str, tuple[str, float]] = {}

# user id -> monotonic times of recent requests.
_recent: dict[str, deque[float]] = {}


def _forget_expired(now: float) -> None:
    if len(_verified) > 5000:
        for key in [k for k, (_, exp) in _verified.items() if exp <= now]:
            _verified.pop(key, None)


async def _user_for(token: str) -> str:
    now = time.monotonic()
    key = hashlib.sha256(token.encode()).hexdigest()
    cached = _verified.get(key)
    if cached and cached[1] > now:
        return cached[0]

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Your sign-in has expired. Please sign in to Awarna again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = (response.json() or {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please sign in to Awarna again.")

    _forget_expired(now)
    _verified[key] = (user_id, now + settings.AUTH_CACHE_SECONDS)
    return user_id


def _rate_limit(user_id: str) -> None:
    now = time.monotonic()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    hits = _recent.setdefault(user_id, deque())
    while hits and hits[0] <= now - window:
        hits.popleft()

    if len(hits) >= settings.RATE_LIMIT_REQUESTS:
        retry_after = int(window - (now - hits[0])) + 1
        logger.warning("Rate limit reached for user=%s", user_id)
        raise HTTPException(
            status_code=429,
            detail="That is a lot of documents at once. Please wait a few minutes and try again.",
            headers={"Retry-After": str(retry_after)},
        )

    hits.append(now)


async def require_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: returns the signed-in user's id or refuses the request."""

    if not settings.REQUIRE_AUTH:
        return "anonymous"

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Please sign in to Awarna to use Smart scan.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    try:
        user_id = await _user_for(token)
    except httpx.HTTPError as exc:
        logger.error("Could not reach Supabase to check a sign-in: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Could not check your sign-in just now. Please try again.",
        ) from exc

    _rate_limit(user_id)
    return user_id
