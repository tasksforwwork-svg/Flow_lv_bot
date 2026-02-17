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

    # Порядок важен! transactions ДО categories
    dp.include_router(start.router)
    dp.include_router(transactions.router)
    dp.include_router(reports.router)
    dp.include_router(budgets.router)
    dp.include_router(manage.router)      # ← Добавили
    dp.include_router(categories.router)

    try:
        me = await bot.get_me()
        print(f"✅ Бот запущен: @{me.username}")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
