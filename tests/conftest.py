import os

# Тестові значення задаються ДО імпорту app, щоб не потрібен був справжній .env
os.environ["BOT_TOKEN"] = "123456:TEST-TOKEN"
os.environ["CHANNEL_ID"] = "-1001234567890"
os.environ["API_KEYS"] = "test-key"
os.environ["APP_ENV"] = "development"
os.environ["RATE_LIMIT_PER_MINUTE"] = "100"
os.environ["DEMO_ENABLED"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def client(notifier: FakeNotifier):
    from app.api.deps import get_notifier
    from app.main import app

    app.dependency_overrides[get_notifier] = lambda: notifier
    # Без "with": lifespan (справжній бот) не запускається
    yield TestClient(app)
    app.dependency_overrides.clear()