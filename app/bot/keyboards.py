from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Авторизоваться по телефону",
                    callback_data="auth:phone",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Ввести Tinder token (тест)",
                    callback_data="auth:token",
                )
            ],
        ]
    )


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мой профиль")],
            [KeyboardButton(text="Запустить AutoSwipe")],
        ],
        resize_keyboard=True,
    )
