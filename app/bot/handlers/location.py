from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_keyboard
from app.bot.states import MainStates
from app.services.location import LocationService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager


def create_router(sessions: TinderSessionManager) -> Router:
    router = Router()

    @router.message(F.text == "Запустить AutoSwipe")
    async def location_start(message: Message, state: FSMContext):
        await state.set_state(MainStates.waiting_location)
        await message.answer("Напиши город, в котором нужно искать анкеты.")

    @router.message(MainStates.waiting_location)
    async def location_received(message: Message, state: FSMContext):
        city = (message.text or "").strip()
        if not city:
            await message.answer("Город не должен быть пустым.")
            return

        client = sessions.get_client(message.from_user.id)
        location_service = LocationService(client)

        try:
            location = location_service.set_city(city)
            recommendations = RecommendationService(client).get_batch()
        except Exception as exc:
            await message.answer(
                f"Не удалось установить город или получить рекомендации: {exc}"
            )
            return

        await state.clear()
        await message.answer(
            f"Город установлен: {location.address or city}\n"
            f"Получено рекомендаций: {len(recommendations)}",
            reply_markup=main_keyboard(),
        )

    return router
