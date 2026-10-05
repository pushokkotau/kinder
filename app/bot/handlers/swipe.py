from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_keyboard
from app.bot.states import MainStates
from app.services.auto_swipe import AutoSwipeService
from app.services.location import LocationService
from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
from app.services.session import TinderSessionManager
from app.services.swipe import SwipeService


def create_router(sessions: TinderSessionManager) -> Router:
    router = Router()

    @router.message(F.text == "Запустить AutoSwipe")
    async def swipe_start(message: Message, state: FSMContext):
        try:
            sessions.get_authenticated_client(message.from_user.id)
        except Exception as exc:
            await message.answer(f"Сначала авторизуй Tinder: {exc}")
            return

        await state.set_state(MainStates.waiting_location)
        await message.answer("Напиши город, в котором нужно искать анкеты.")

    @router.message(MainStates.swiping)
    async def swiping_placeholder(message: Message):
        await message.answer("AutoSwipe уже выполняется. Подожди завершения.")

    @router.message(MainStates.waiting_location, F.text)
    async def location_received(message: Message, state: FSMContext):
        city = message.text.strip()
        if not city:
            await message.answer("Город не должен быть пустым.")
            return

        try:
            client = sessions.get_authenticated_client(message.from_user.id)
        except Exception as exc:
            await state.clear()
            await message.answer(f"Сначала авторизуй Tinder: {exc}")
            return

        await state.set_state(MainStates.swiping)

        recommendation_service = RecommendationService(client)
        service = AutoSwipeService(
            location_service=LocationService(client),
            recommendation_service=recommendation_service,
            match_service=MatchService(client),
            swipe_service=SwipeService(client, recommendation_service),
        )

        await message.answer("Запускаю AutoSwipe...")

        try:
            result = service.run(city)
        except Exception as exc:
            await state.clear()
            await message.answer(
                f"AutoSwipe не удалось завершить: {exc}",
                reply_markup=main_keyboard(),
            )
            return

        await state.clear()
        swipe = result.swipe_result
        matches = result.match_stats
        status = (
            "Лимит достигнут"
            if swipe.limit_reached
            else "Рекомендации закончились"
        )

        await message.answer(
            f"AutoSwipe завершён.\n\n"
            f"Город: {result.location.address or city}\n"
            f"Получено рекомендаций: {result.recommendations_received}\n"
            f"Свайпов выполнено: {swipe.swipes}\n"
            f"Лайков: {swipe.likes}\n"
            f"Дизлайков: {swipe.dislikes}\n"
            f"Новых матчей: {matches.new_matches}\n"
            f"Всего матчей: {matches.after}\n"
            f"Статус: {status}",
            reply_markup=main_keyboard(),
        )

    return router
