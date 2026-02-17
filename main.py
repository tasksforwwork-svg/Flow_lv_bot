import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

from handlers import start, categories, transactions, reports
from database.models import create_tables

# Включаем логирование, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)

async def main():
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не найден! Проверь переменные окружения.")
        return

    print("✅ Токен найден, пытаемся запустить...")
    
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(categories.router)
    dp.include_router(transactions.router)
    dp.include_router(reports.router)

    try:
        # Проверка связи с Telegram
        me = await bot.get_me()
        print(f"✅ Бот запущен: @{me.username}")
        
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
