import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage # Важно для FSM
from config import BOT_TOKEN

from handlers import start
from handlers import categories
from handlers import transactions
from handlers import reports # Добавили отчеты

from database.models import create_tables

async def main():
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    # Используем MemoryStorage для хранения состояний FSM
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(categories.router)
    dp.include_router(transactions.router)
    dp.include_router(reports.router) # Подключили роутер отчетов

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
