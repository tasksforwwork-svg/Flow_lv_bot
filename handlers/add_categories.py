from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_connection

router = Router()

# ✅ ТВОЙ ID:
ADMIN_ID = 534808305


@router.message(Command("fixcategories"))
async def fix_all_categories(message: Message):
    """
    Универсальная команда для исправления всех категорий:
    - Удаляет "Вокал"
    - Добавляет подкатегории в "Еда"
    - Создаёт "Мелочи" и добавляет подкатегории
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещён")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        conn.close()
        return
    
    user_id = user["id"]
    added = []
    removed = []
    
    # ===== 1. УДАЛЯЕМ "ВОКАЛ" =====
    cursor.execute(
        "DELETE FROM categories WHERE name = 'Вокал' AND user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    if cursor.rowcount > 0:
        removed.append("Вокал (категория)")
    
    # ===== 2. ДОБАВЛЯЕМ ПОДКАТЕГОРИИ В "ЕДА" =====
    food_subcats = ["Сладости", "Перекус"]
    
    cursor.execute(
        "SELECT id FROM categories WHERE name = 'Еда' AND user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    food_parent = cursor.fetchone()
    
    if food_parent:
        for subcat in food_subcats:
            cursor.execute(
                "SELECT id FROM categories WHERE name = ? AND parent_id = ? AND user_id = ?",
                (subcat, food_parent["id"], user_id)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                    (user_id, subcat, food_parent["id"])
                )
                added.append(f"Еда → {subcat}")
    else:
        removed.append("⚠️ Категория 'Еда' не найдена")
    
    # ===== 3. СОЗДАЁМ "МЕЛОЧИ" И ДОБАВЛЯЕМ ПОДКАТЕГОРИИ =====
    # Сначала создаём саму категорию "Мелочи"
    cursor.execute(
        "SELECT id FROM categories WHERE name = 'Мелочи' AND user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    misc_parent = cursor.fetchone()
    
    if not misc_parent:
        cursor.execute(
            "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, NULL)",
            (user_id, "Мелочи")
        )
        misc_parent_id = cursor.lastrowid
        added.append("Мелочи (новая категория)")
    else:
        misc_parent_id = misc_parent["id"]
    
    # Подкатегории для "Мелочи"
    misc_subcats = ["Дом", "Канцелярия", "Прочее"]
    
    for subcat in misc_subcats:
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND parent_id = ? AND user_id = ?",
            (subcat, misc_parent_id, user_id)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, subcat, misc_parent_id)
            )
            added.append(f"Мелочи → {subcat}")
    
    conn.commit()
    conn.close()
    
    # ===== ФОРМИРУЕМ ОТЧЁТ =====
    text = "✅ **Обновление категорий завершено!**\n\n"
    
    if removed:
        text += "**Удалено:**\n"
        for item in removed:
            text += f"• {item}\n"
        text += "\n"
    
    if added:
        text += "**Добавлено:**\n"
        for item in added:
            text += f"• {item}\n"
        text += "\n"
    
    text += "🔄 **Теперь отправь /start для обновления меню!**"
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("myid"))
async def show_id(message: Message):
    await message.answer(f"Твой ID: {message.from_user.id}")
