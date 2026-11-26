import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_notifier, rate_limit, verify_api_key
from app.config import Settings, get_settings
from app.schemas.feedback import FeedbackAccepted, FeedbackIn
from app.services.formatter import format_feedback
from app.services.notifier import NotificationError, TelegramNotifier

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/v1/feedback",
    response_model=FeedbackAccepted,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit), Depends(verify_api_key)],
    tags=["feedback"],
)
async def create_feedback(
    payload: FeedbackIn,
    notifier: TelegramNotifier = Depends(get_notifier),
    settings: Settings = Depends(get_settings),
) -> FeedbackAccepted:
    feedback_id = uuid4().hex[:12]
    text = format_feedback(payload, feedback_id, settings.timezone)

    try:
        await notifier.send(text)
    except NotificationError:
        logger.exception("Failed to deliver feedback %s", feedback_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback service is temporarily unavailable",
        )

    # Текст відгуку в логи не пишемо (приватність)
    logger.info("Feedback %s (%s) delivered", feedback_id, payload.type.value)
    return FeedbackAccepted(id=feedback_id)