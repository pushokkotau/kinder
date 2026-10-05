import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import auth, location, profile, start, swipe
from app.services.session import TinderSessionManager


def create_dispatcher() -> Dispatcher:
    bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    sessions = TinderSessionManager()

    dp.include_router(start.router)
    dp.include_router(auth.create_router(sessions))
    dp.include_router(profile.create_router(sessions))
    dp.include_router(location.create_router(sessions))
    dp.include_router(swipe.create_router(sessions))

    return dp


async def main() -> None:
    bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
