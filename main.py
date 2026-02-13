import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start, transactions
from database.models import create_tables   # ← добавили

async def main():
    create_tables()  # ← добавили

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(transactions.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())