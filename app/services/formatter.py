from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from app.schemas.feedback import FeedbackIn, FeedbackType

_TYPE_META: dict[FeedbackType, tuple[str, str]] = {
    FeedbackType.FEEDBACK: ("💬", "Відгук"),
    FeedbackType.COMPLAINT: ("⚠️", "Скарга"),
    FeedbackType.BUG: ("🐞", "Баг"),
    FeedbackType.SUGGESTION: ("💡", "Пропозиція"),
}


def format_feedback(feedback: FeedbackIn, feedback_id: str, timezone: str) -> str:
    """Збирає HTML-повідомлення для Telegram. Увесь текст від користувача екранується."""
    emoji, title = _TYPE_META[feedback.type]
    now = datetime.now(ZoneInfo(timezone)).strftime("%d.%m.%Y %H:%M")

    # Хештег дозволяє фільтрувати повідомлення в каналі: #bug, #complaint тощо
    lines = [f"{emoji} <b>{title}</b>  #{feedback.type.value}"]

    if feedback.rating is not None:
        stars = "⭐" * feedback.rating + "☆" * (5 - feedback.rating)
        lines.append(f"<b>Оцінка:</b> {stars}")

    lines.append(f"<blockquote>{escape(feedback.message)}</blockquote>")

    details = (
        ("Користувач", feedback.user_id),
        ("Контакт", feedback.contact),
        ("Платформа", feedback.platform),
        ("Версія", feedback.app_version),
        ("Мова", feedback.locale),
    )
    for label, value in details:
        if value:
            lines.append(f"<b>{label}:</b> <code>{escape(str(value))}</code>")

    lines.append(f"<b>Час:</b> {now}")
    lines.append(f"<b>ID:</b> <code>{feedback_id}</code>")
    return "\n".join(lines)