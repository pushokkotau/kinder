from types import SimpleNamespace

import pytest

from app.bot.handlers import swipe
from app.bot.handlers.swipe import create_router
from app.bot.states import MainStates
from app.tinder.client import TinderAPIError
from app.tinder.models import MatchStats, SwipeResult
from app.services.auto_swipe import AutoSwipeResult


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


def test_authenticated_user_can_start_autoswipe():
    services = SimpleNamespace(autoswipe=object())
    provider = SimpleNamespace(
        for_message=lambda message, authenticated=False: services
    )
    router = create_router(provider)
    start = handler(router, "swipe_start")
    message = FakeMessage()
    state = FakeState()

    pytest.run(asyncio_run(start(message, state)))


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
