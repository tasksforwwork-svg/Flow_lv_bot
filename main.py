import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

from handlers import start, categories, transactions, reports, budgets, add_categories, edit_transaction
from database.models import create_tables

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

async def main():
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не найден!")
        return

    print("✅ Токен найден, запускаем бота...")
    
    # Создаём таблицы в БД
    create_tables()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ⚠️ ВАЖНО: Порядок подключения роутеров!
    # categories.router должен быть ПОСЛЕДНИМ
    dp.include_router(start.router)              # 1. Start
    dp.include_router(transactions.router)       # 2. Транзакции
    dp.include_router(reports.router)            # 3. Отчёты
    dp.include_router(budgets.router)            # 4. Бюджеты
    dp.include_router(add_categories.router)     # 5. Добавление категорий
    dp.include_router(edit_transaction.router)   # 6. Редактирование
    dp.include_router(categories.router)         # 7. Категории (ПОСЛЕДНИМ!)

    try:
        # Проверка связи с Telegram
        me = await bot.get_me()
        print(f"✅ Бот успешно запущен: @{me.username}")
        print(f"🤖 ID бота: {me.id}")
        
        # Запуск polling
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
