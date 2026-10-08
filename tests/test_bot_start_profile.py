from types import SimpleNamespace

import pytest

from app.bot.handlers.profile import create_router
from app.bot.handlers.start import start
from app.tinder.client import TinderAPIError
from app.tinder.models import Profile


class FakeMessage:
    def __init__(self, text="", user_id=42):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeProvider:
    def __init__(self, services):
        self.services = services
        self.calls = []

    def for_message(self, message, *, authenticated=False):
        self.calls.append((message.from_user.id, authenticated))
        return self.services


def _run_sync(func, *args):
    async def runner():
        return func(*args)

    return runner()


@pytest.mark.asyncio
async def test_start_shows_authentication_button():
    message = FakeMessage()

    await start(message)

    assert message.answers[0][0] == (
        "Привет! Для работы бота сначала авторизуй Tinder."
    )
    markup = message.answers[0][1]["reply_markup"]
    assert markup.inline_keyboard[0][0].text == "Авторизоваться по телефону"
    assert markup.inline_keyboard[1][0].text == "Ввести Tinder token (тест)"


@pytest.mark.asyncio
async def test_profile_uses_authenticated_service_and_shows_profile(monkeypatch):
    profile = SimpleNamespace(
        get_profile=lambda: Profile(
            name="Alex",
            city="Amsterdam",
            country="Netherlands",
        )
    )
    provider = FakeProvider(SimpleNamespace(profile=profile))
    message = FakeMessage("Мой профиль")

    monkeypatch.setattr(
        "app.bot.handlers.profile.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    router = create_router(provider)
    handler = router.message.handlers[0].callback

    await handler(message)

    assert provider.calls == [(42, True)]
    assert message.answers == [
        (
            "Имя: Alex\nГород: Amsterdam\nСтрана: Netherlands",
            {},
        )
    ]


@pytest.mark.asyncio
async def test_profile_reports_tinder_error(monkeypatch):
    def fail():
        raise TinderAPIError("Tinder is unavailable")

    provider = FakeProvider(SimpleNamespace(profile=SimpleNamespace(get_profile=fail)))
    message = FakeMessage("Мой профиль")

    monkeypatch.setattr(
        "app.bot.handlers.profile.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    router = create_router(provider)
    handler = router.message.handlers[0].callback

    await handler(message)

    assert message.answers == [
        ("Не удалось получить профиль Tinder: Tinder is unavailable", {})
    ]
