from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from app.bot.keyboards import start_keyboard


router = Router()


@router.message(Command("start"), StateFilter("*"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Для работы бота сначала авторизуй Tinder.",
        reply_markup=start_keyboard(),
    )
