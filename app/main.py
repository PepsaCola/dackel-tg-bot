import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.rate_limit import RateLimiter
from app.services.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    # Перевіряємо токен під час старту: з неправильним токеном сервіс не запуститься
    me = await bot.get_me()
    logger.info("Bot @%s started, channel %s", me.username, settings.channel_id)

    app.state.notifier = TelegramNotifier(bot, settings.channel_id)
    try:
        yield
    finally:
        await bot.session.close()
        logger.info("Bot session closed")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Feedback Bot",
        version="1.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.rate_limiter = RateLimiter(limit=settings.rate_limit_per_minute)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["POST"],
            allow_headers=["Content-Type", "X-API-Key"],
        )

    app.include_router(router)

    # Демо-сторінка з прикладом підключення: http://<host>/demo/
    if settings.demo_enabled:
        app.mount("/demo", StaticFiles(directory=WEB_DIR, html=True), name="demo")
        logger.info("Demo page enabled at /demo/")

    return app


app = create_app()