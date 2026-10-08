import asyncio

from aiogram import F, Router
from aiogram.types import Message

from app.bot.services import TelegramServiceProvider
from app.tinder.client import TinderAPIError


def create_router(services_provider: TelegramServiceProvider) -> Router:
    router = Router()

    @router.message(F.text == "Мой профиль")
    async def profile(message: Message):
        try:
            service = services_provider.for_message(
                message,
                authenticated=True,
            ).profile
            tinder_profile = await asyncio.to_thread(service.get_profile)
        except TinderAPIError as exc:
            await message.answer(f"Не удалось получить профиль Tinder: {exc}")
            return

        await message.answer(
            f"Имя: {tinder_profile.name}\n"
            f"Город: {tinder_profile.city}\n"
            f"Страна: {tinder_profile.country}"
        )

    return router
