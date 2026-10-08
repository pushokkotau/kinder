import asyncio

from aiogram import F, Router
from aiogram.types import Message

from app.services.factory import ServiceFactory
from app.services.session import TinderSessionManager


def create_router(sessions: TinderSessionManager) -> Router:
    router = Router()

    @router.message(F.text == "Мой профиль")
    async def profile(message: Message):
        try:
            client = sessions.get_authenticated_client(message.from_user.id)
            service = ServiceFactory.for_client(client).profile
            tinder_profile = await asyncio.to_thread(service.get_profile)
        except Exception as exc:
            await message.answer(f"Не удалось получить профиль Tinder: {exc}")
            return

        await message.answer(
            f"Имя: {tinder_profile.name}\\n"
            f"Город: {tinder_profile.city}\\n"
            f"Страна: {tinder_profile.country}"
        )

    return router
