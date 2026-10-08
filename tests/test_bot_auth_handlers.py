from types import SimpleNamespace

import pytest

from app.bot.handlers.auth import (
    code_received,
    phone_received,
    token_received,
)
from app.bot.states import AuthStates
from app.tinder.client import TinderAPIError
from app.tinder.models import Profile


class FakeMessage:
    def __init__(self, text, user_id=42):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeState:
    def __init__(self, data=None):
        self.data = {} if data is None else dict(data)
        self.states = []
        self.clear_calls = 0

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.states.append(state)

    async def clear(self):
        self.clear_calls += 1
        self.data.clear()


def provider_for(services):
    return SimpleNamespace(for_message=lambda message: services)


@pytest.mark.asyncio
async def test_phone_received_normalizes_phone_and_requests_code(monkeypatch):
    calls = []
    auth = SimpleNamespace(
        request_phone_code=lambda phone: calls.append(phone),
    )
    services = SimpleNamespace(auth=auth)
    provider = provider_for(services)
    state = FakeState()
    message = FakeMessage("+31 6 1234 5678")

    monkeypatch.setattr(
        "app.bot.handlers.auth.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await phone_received(message, state, provider)

    assert calls == ["+31612345678"]
    assert state.data == {"phone": "+31612345678"}
    assert state.states == [AuthStates.waiting_code]
    assert message.answers == [
        ("Код отправлен. Теперь отправь код из Tinder.", {})
    ]


@pytest.mark.asyncio
async def test_phone_received_rejects_invalid_phone():
    services = SimpleNamespace(auth=object())
    provider = provider_for(services)
    state = FakeState()
    message = FakeMessage("not-a-phone")

    await phone_received(message, state, provider)

    assert state.states == []
    assert state.data == {}
    assert message.answers == [
        (
            "Не удалось распознать номер. Отправь его в международном формате, "
            "например +31612345678.",
            {},
        )
    ]


@pytest.mark.asyncio
async def test_phone_received_reports_tinder_error(monkeypatch):
    def fail(phone):
        raise TinderAPIError("Tinder is unavailable")

    services = SimpleNamespace(
        auth=SimpleNamespace(request_phone_code=fail),
    )
    provider = provider_for(services)
    state = FakeState()
    message = FakeMessage("+31612345678")

    monkeypatch.setattr(
        "app.bot.handlers.auth.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await phone_received(message, state, provider)

    assert state.states == []
    assert state.data == {}
    assert message.answers == [
        ("Не удалось запросить код Tinder: Tinder is unavailable", {})
    ]


@pytest.mark.asyncio
async def test_code_received_authenticates_and_shows_profile(monkeypatch):
    calls = []
    auth = SimpleNamespace(
        authenticate_with_code=lambda phone, code: calls.append((phone, code)),
    )
    profile = SimpleNamespace(
        get_profile=lambda: Profile(
            name="Alex",
            city="Amsterdam",
            country="Netherlands",
        )
    )
    services = SimpleNamespace(auth=auth, profile=profile)
    provider = provider_for(services)
    state = FakeState({"phone": "+31612345678"})
    message = FakeMessage("123456")

    monkeypatch.setattr(
        "app.bot.handlers.auth.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await code_received(message, state, provider)

    assert calls == [("+31612345678", "123456")]
    assert state.clear_calls == 1
    assert message.answers[0][0] == (
        "Авторизация успешна!\n"
        "Профиль: Alex\n"
        "Город: Amsterdam\n"
        "Страна: Netherlands"
    )
    assert "reply_markup" in message.answers[0][1]


@pytest.mark.asyncio
async def test_token_received_authenticates_and_shows_profile(monkeypatch):
    calls = []
    auth = SimpleNamespace(
        authenticate_with_token=lambda token: calls.append(token),
    )
    profile = SimpleNamespace(
        get_profile=lambda: Profile(
            name="Alex",
            city="Amsterdam",
            country="Netherlands",
        )
    )
    services = SimpleNamespace(auth=auth, profile=profile)
    provider = provider_for(services)
    state = FakeState()
    message = FakeMessage("test-token")

    monkeypatch.setattr(
        "app.bot.handlers.auth.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await token_received(message, state, provider)

    assert calls == ["test-token"]
    assert state.clear_calls == 1
    assert message.answers[0][0] == (
        "Авторизация успешна!\n"
        "Профиль: Alex\n"
        "Город: Amsterdam\n"
        "Страна: Netherlands"
    )
    assert "reply_markup" in message.answers[0][1]


def _run_sync(func, *args):
    import asyncio

    async def runner():
        return func(*args)

    return runner()
