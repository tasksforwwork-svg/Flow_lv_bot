import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

from handlers import start, categories, transactions, reports, budgets, manage
from database.models import create_tables

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не найден!")
        return

    print("✅ Токен найден, запускаем...")
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ⚠️ ВАЖНЫЙ ПОРЯДОК:
    dp.include_router(start.router)           # 1
    dp.include_router(transactions.router)    # 2 - ДО categories
    dp.include_router(manage.router)          # 3 - ДО categories  
    dp.include_router(reports.router)         # 4
    dp.include_router(budgets.router)         # 5
    dp.include_router(categories.router)      # 6 - ПОСЛЕДНИМ!

    try:
        me = await bot.get_me()
        print(f"✅ Бот запущен: @{me.username}")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
