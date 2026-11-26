import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Не вдалося доставити повідомлення в Telegram."""


class TelegramNotifier:
    _MAX_RETRY_AFTER_SECONDS = 30

    def __init__(self, bot: Bot, channel_id: int, max_attempts: int = 3) -> None:
        self._bot = bot
        self._channel_id = channel_id
        self._max_attempts = max_attempts

    async def send(self, text: str) -> None:
        for attempt in range(1, self._max_attempts + 1):
            try:
                await self._bot.send_message(chat_id=self._channel_id, text=text)
                return
            except TelegramRetryAfter as exc:
                # Telegram просить зачекати (флуд-контроль)
                if exc.retry_after > self._MAX_RETRY_AFTER_SECONDS:
                    raise NotificationError(f"Flood control: retry after {exc.retry_after}s") from exc
                logger.warning("Flood control, sleeping %ss (attempt %s)", exc.retry_after, attempt)
                await asyncio.sleep(exc.retry_after)
            except TelegramNetworkError as exc:
                logger.warning("Telegram network error (attempt %s): %s", attempt, exc)
                if attempt == self._max_attempts:
                    raise NotificationError("Telegram is unreachable") from exc
                await asyncio.sleep(2**attempt)
            except TelegramAPIError as exc:
                # Повтор не допоможе: неправильний CHANNEL_ID, бот не адміністратор тощо
                raise NotificationError(f"Telegram API error: {exc}") from exc

        raise NotificationError("Failed to deliver message after retries")