import asyncio

from geopy.exc import GeocoderServiceError

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_keyboard
from app.bot.services import TelegramServiceProvider
from app.bot.states import MainStates
from app.tinder.client import TinderAPIError


def create_router(services_provider: TelegramServiceProvider) -> Router:
    router = Router()

    @router.message(F.text == "Запустить AutoSwipe")
    async def swipe_start(message: Message, state: FSMContext):
        try:
            services_provider.for_message(message, authenticated=True)
        except TinderAPIError as exc:
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
            services = services_provider.for_message(
                message,
                authenticated=True,
            )
        except TinderAPIError as exc:
            await state.clear()
            await message.answer(f"Сначала авторизуй Tinder: {exc}")
            return

        await state.set_state(MainStates.swiping)

        service = services.autoswipe

        await message.answer("Запускаю AutoSwipe...")

        try:
            result = await asyncio.to_thread(service.run, city)
        except (TinderAPIError, ValueError, GeocoderServiceError) as exc:
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
