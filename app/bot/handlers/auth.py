import asyncio

import phonenumbers

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_keyboard
from app.bot.services import TelegramServiceProvider
from app.bot.states import AuthStates
from app.tinder.client import TinderAPIError


async def phone_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AuthStates.waiting_phone)
    await callback.message.answer(
        "Отправь номер телефона в международном формате, например +31612345678."
    )
    await callback.answer()


async def token_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AuthStates.waiting_test_token)
    await callback.message.answer(
        "Отправь Tinder token. Этот способ нужен только для тестирования."
    )
    await callback.answer()


async def phone_received(
    message: Message,
    state: FSMContext,
    services_provider: TelegramServiceProvider,
) -> None:
    raw_phone = (message.text or "").strip()
    try:
        parsed = phonenumbers.parse(raw_phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError
        phone = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )
    except (phonenumbers.NumberParseException, ValueError):
        await message.answer(
            "Не удалось распознать номер. Отправь его в международном формате, "
            "например +31612345678."
        )
        return

    services = services_provider.for_message(message)
    try:
        await asyncio.to_thread(services.auth.request_phone_code, phone)
    except TinderAPIError as exc:
        await message.answer(f"Не удалось запросить код Tinder: {exc}")
        return

    await state.update_data(phone=phone)
    await state.set_state(AuthStates.waiting_code)
    await message.answer("Код отправлен. Теперь отправь код из Tinder.")


async def code_received(
    message: Message,
    state: FSMContext,
    services_provider: TelegramServiceProvider,
) -> None:
    data = await state.get_data()
    phone = data.get("phone")
    code = (message.text or "").strip()

    if not phone:
        await state.clear()
        await message.answer("Сессия авторизации потеряна. Начни заново через /start.")
        return

    services = services_provider.for_message(message)
    try:
        await asyncio.to_thread(services.auth.authenticate_with_code, phone, code)
        tinder_profile = await asyncio.to_thread(services.profile.get_profile)
    except TinderAPIError as exc:
        await message.answer(f"Не удалось завершить авторизацию: {exc}")
        return

    await state.clear()
    await message.answer(
        f"Авторизация успешна!\n"
        f"Профиль: {tinder_profile.name}\n"
        f"Город: {tinder_profile.city}\n"
        f"Страна: {tinder_profile.country}",
        reply_markup=main_keyboard(),
    )


async def token_received(
    message: Message,
    state: FSMContext,
    services_provider: TelegramServiceProvider,
) -> None:
    token = (message.text or "").strip()
    if not token:
        await message.answer("Token не должен быть пустым.")
        return

    services = services_provider.for_message(message)
    try:
        await asyncio.to_thread(services.auth.authenticate_with_token, token)
        tinder_profile = await asyncio.to_thread(services.profile.get_profile)
    except TinderAPIError as exc:
        await message.answer(
            f"Token не подошёл или Tinder API недоступен: {exc}"
        )
        return

    await state.clear()
    await message.answer(
        f"Авторизация успешна!\n"
        f"Профиль: {tinder_profile.name}\n"
        f"Город: {tinder_profile.city}\n"
        f"Страна: {tinder_profile.country}",
        reply_markup=main_keyboard(),
    )


def create_router(services_provider: TelegramServiceProvider) -> Router:
    router = Router()

    @router.callback_query(F.data == "auth:phone")
    async def phone_callback(callback: CallbackQuery, state: FSMContext):
        await phone_start(callback, state)

    @router.callback_query(F.data == "auth:token")
    async def token_callback(callback: CallbackQuery, state: FSMContext):
        await token_start(callback, state)

    @router.message(AuthStates.waiting_phone)
    async def phone_handler(message: Message, state: FSMContext):
        await phone_received(message, state, services_provider)

    @router.message(AuthStates.waiting_code)
    async def code_handler(message: Message, state: FSMContext):
        await code_received(message, state, services_provider)

    @router.message(AuthStates.waiting_test_token)
    async def token_handler(message: Message, state: FSMContext):
        await token_received(message, state, services_provider)

    return router
