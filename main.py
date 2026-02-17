import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

# Импортируем все модули обработчиков
from handlers import start, categories, transactions, reports, budgets, manage
from database.models import create_tables

# Настраиваем логирование для отладки
logging.basicConfig(level=logging.INFO)

async def main():
    # Проверка токена
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не найден! Проверь переменные окружения.")
        return

    print("✅ Токен найден, запускаем бота...")
    
    # Создаем таблицы в БД при запуске
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    # Используем MemoryStorage для хранения состояний FSM
    dp = Dispatcher(storage=MemoryStorage())

    # ⚠️ ВАЖНО: Порядок подключения роутеров имеет значение!
    # 1. Start - всегда первый
    dp.include_router(start.router)
    
    # 2. Transactions - должен быть ДО categories, чтобы перехватывать сообщения вида "100 кофе"
    dp.include_router(transactions.router)
    
    # 3. Manage - редактирование и удаление (должен быть до категорий)
    dp.include_router(manage.router)
    
    # 4. Reports и Budgets - обычные команды
    dp.include_router(reports.router)
    dp.include_router(budgets.router)
    
    # 5. Categories - всегда последний, так как содержит универсальные обработчики
    dp.include_router(categories.router)

    try:
        # Проверка связи с Telegram
        me = await bot.get_me()
        print(f"✅ Бот успешно запущен: @{me.username}")
        
        # Запуск polling
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
