import secrets

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.notifier import TelegramNotifier


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_api_key or not any(
        secrets.compare_digest(x_api_key, key) for key in settings.api_key_list
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def rate_limit(request: Request) -> None:
    limiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.hit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, try again later",
        )


def get_notifier(request: Request) -> TelegramNotifier:
    return request.app.state.notifier