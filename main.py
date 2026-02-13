import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

from handlers import start
from handlers import categories
from handlers import transactions

from database.models import create_tables


async def main():
    # Создаём таблицы при запуске
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ВАЖНО: порядок подключения роутеров
    dp.include_router(start.router)
    dp.include_router(categories.router)
    dp.include_router(transactions.router)

    # Запуск
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
