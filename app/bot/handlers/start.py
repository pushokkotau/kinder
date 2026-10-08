from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from app.bot.keyboards import start_keyboard, unauthenticated_keyboard


router = Router()


async def show_authentication_options(message: Message) -> None:
    await message.answer(
        "Выбери способ авторизации Tinder.",
        reply_markup=start_keyboard(),
    )


@router.message(Command("start"), StateFilter("*"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Для работы бота сначала авторизуй Tinder.",
        reply_markup=unauthenticated_keyboard(),
    )


@router.message(F.text == "Авторизоваться")
async def authenticate(message: Message) -> None:
    await show_authentication_options(message)
