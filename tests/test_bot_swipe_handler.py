from types import SimpleNamespace

import pytest

from app.bot.handlers.swipe import create_router
from app.bot.states import MainStates
from app.services.auto_swipe import AutoSwipeResult
from app.tinder.client import TinderAPIError
from app.tinder.models import MatchStats, SwipeResult


class FakeMessage:
    def __init__(self, text="Запустить AutoSwipe", user_id=42):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeState:
    def __init__(self):
        self.states = []
        self.clear_calls = 0

    async def set_state(self, state):
        self.states.append(state)

    async def clear(self):
        self.clear_calls += 1


def handler(router, name):
    return next(
        item.callback
        for item in router.message.handlers
        if item.callback.__name__ == name
    )


@pytest.mark.asyncio
async def test_authenticated_user_can_start_autoswipe():
    services = SimpleNamespace(autoswipe=object())
    provider = SimpleNamespace(
        for_message=lambda message, authenticated=False: services
    )
    router = create_router(provider)
    start = handler(router, "swipe_start")
    message = FakeMessage()
    state = FakeState()

    await start(message, state)

    assert state.states == [MainStates.waiting_location]
    assert message.answers == [
        ("Напиши город, в котором нужно искать анкеты.", {})
    ]


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_start_autoswipe():
    def for_message(message, *, authenticated=False):
        raise TinderAPIError("not authenticated")

    provider = SimpleNamespace(for_message=for_message)
    router = create_router(provider)
    start = handler(router, "swipe_start")
    message = FakeMessage()
    state = FakeState()

    await start(message, state)

    assert state.states == []
    assert message.answers == [
        ("Сначала авторизуй Tinder: not authenticated", {})
    ]


@pytest.mark.asyncio
async def test_autoswipe_success_sends_summary(monkeypatch):
    result = AutoSwipeResult(
        swipe_result=SwipeResult(
            swipes=12,
            likes=6,
            dislikes=6,
            limit_reached=True,
            recommendations_exhausted=False,
            recommendations_received=12,
        ),
        match_stats=MatchStats(before=10, after=16),
        recommendations_received=12,
        location=SimpleNamespace(address="Amsterdam"),
    )
    service = SimpleNamespace(run=lambda city: result)
    services = SimpleNamespace(autoswipe=service)
    provider = SimpleNamespace(
        for_message=lambda message, authenticated=False: services
    )
    router = create_router(provider)
    receive_location = handler(router, "location_received")
    message = FakeMessage(text="Amsterdam")
    state = FakeState()
    monkeypatch.setattr(
        "app.bot.handlers.swipe.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await state.set_state(MainStates.waiting_location)
    await receive_location(message, state)

    assert state.clear_calls == 1
    assert message.answers[0][0] == "Запускаю AutoSwipe..."
    assert message.answers[1][0] == (
        "AutoSwipe завершён.\n\n"
        "Город: Amsterdam\n"
        "Получено рекомендаций: 12\n"
        "Свайпов выполнено: 12\n"
        "Лайков: 6\n"
        "Дизлайков: 6\n"
        "Новых матчей: 6\n"
        "Всего матчей: 16\n"
        "Статус: Лимит достигнут"
    )


@pytest.mark.asyncio
async def test_autoswipe_error_clears_state_and_reports_error(monkeypatch):
    def fail(city):
        raise TinderAPIError("Tinder is unavailable")

    service = SimpleNamespace(run=fail)
    services = SimpleNamespace(autoswipe=service)
    provider = SimpleNamespace(
        for_message=lambda message, authenticated=False: services
    )
    router = create_router(provider)
    receive_location = handler(router, "location_received")
    message = FakeMessage(text="Amsterdam")
    state = FakeState()
    monkeypatch.setattr(
        "app.bot.handlers.swipe.asyncio.to_thread",
        lambda func, *args: _run_sync(func, *args),
    )

    await receive_location(message, state)

    assert state.clear_calls == 1
    assert message.answers[0][0] == "Запускаю AutoSwipe..."
    assert message.answers[1][0] == (
        "AutoSwipe не удалось завершить: Tinder is unavailable"
    )


def _run_sync(func, *args):
    import asyncio

    async def runner():
        return func(*args)

    return runner()
