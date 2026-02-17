from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)
router = Router()

# ⚠️ ВАЖНО: Замени на свой Telegram ID!
# Узнать ID можно через бота @userinfobot
ADMIN_ID = 8434411798  # ← ВСТАВЬ СВОЙ ID СЮДА!


@router.message(Command("addcategories"))
async def add_missing_categories(message: Message):
    """
    Команда для добавления новых подкатегорий существующему пользователю
    Использование: /addcategories
    """
    # Проверяем, что это админ
    if message.from_user.id != ADMIN_ID:
        logger.warning(f"Попытка доступа от {message.from_user.id}")
        return
    
    user_telegram_id = message.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем user_id из БД
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_telegram_id,))
    user = cursor.fetchone()
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе")
        conn.close()
        return
    
    user_id = user["id"]
    added = []
    skipped = []
    
    # Категории для добавления
    new_subcategories = {
        "Еда": ["Кофе"],
        "Развлечения": ["ЧГК", "Квизы"]
    }
    
    for parent_name, children in new_subcategories.items():
        # Находим родительскую категорию
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND user_id = ? AND parent_id IS NULL",
            (parent_name, user_id)
        )
        parent = cursor.fetchone()
        
        if not parent:
            logger.error(f"Категория {parent_name} не найдена")
            continue
        
        for child_name in children:
            # Проверяем, есть ли уже такая подкатегория
            cursor.execute(
                "SELECT id FROM categories WHERE name = ? AND parent_id = ? AND user_id = ?",
                (child_name, parent["id"], user_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                skipped.append(f"{parent_name} → {child_name} (уже есть)")
                continue
            
            # Добавляем подкатегорию
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, child_name, parent["id"])
            )
            added.append(f"{parent_name} → {child_name}")
    
    conn.commit()
    conn.close()
    
    # Формируем ответ
    text = "✅ **Обновление категорий завершено!**\n\n"
    
    if added:
        text += "**Добавлено:**\n"
        for item in added:
            text += f"• {item}\n"
        text += "\n"
    
    if skipped:
        text += "**Пропущено (уже существуют):**\n"
        for item in skipped:
            text += f"• {item}\n"
    
    text += "\nТеперь перезапустите бота командой /start"
    
    await message.answer(text, parse_mode="Markdown")