from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)
router = Router()

ADMIN_ID = 534808305

@router.message(Command("fixcategories"))
async def fix_all_categories(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    logger.info("=== ЗАПУСК FIX CATEGORIES ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 🔥 ВАЖНО: Создаём пользователя, если нет
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )
    conn.commit()
    
    # Теперь получаем user_id
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        logger.error("Не удалось создать пользователя")
        await message.answer("❌ Ошибка создания пользователя")
        return
    
    user_id = user["id"]
    logger.info(f"User ID: {user_id}")
    
    # 1. Удаляем Вокал
    cursor.execute("DELETE FROM categories WHERE name LIKE '%Вокал%' AND user_id = ?", (user_id,))
    deleted = cursor.rowcount
    logger.info(f"Удалено категорий 'Вокал': {deleted}")
    
    # 2. Добавляем Сладости и Перекус в Еду
    cursor.execute("SELECT id FROM categories WHERE name = 'Еда' AND user_id = ?", (user_id,))
    food = cursor.fetchone()
    
    if food:
        cursor.execute("INSERT OR IGNORE INTO categories (user_id, name, parent_id) VALUES (?, 'Сладости', ?)", (user_id, food["id"]))
        cursor.execute("INSERT OR IGNORE INTO categories (user_id, name, parent_id) VALUES (?, 'Перекус', ?)", (user_id, food["id"]))
        logger.info("Добавлены: Сладости, Перекус")
    else:
        logger.warning("Категория 'Еда' не найдена!")
    
    # 3. Создаем Мелочи
    cursor.execute("INSERT OR IGNORE INTO categories (user_id, name, parent_id) VALUES (?, 'Мелочи', NULL)", (user_id,))
    logger.info("Создана категория: Мелочи")
    
    conn.commit()
    conn.close()
    
    await message.answer("✅ ГОТОВО! Теперь жми /start")
    logger.info("=== ФИНИШ ===")

@router.message(Command("myid"))
async def show_id(message: Message):
    await message.answer(f"Твой ID: {message.from_user.id}")
