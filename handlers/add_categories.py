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
    Исправление категорий:
    - Удаляет "Вокал"
    - Создаёт "Мелочи"
    - Добавляет подкатегории в "Еда": Сладости, Перекус
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
    cursor.execute("""
        SELECT id, name FROM categories 
        WHERE user_id = ? AND parent_id IS NULL 
        AND LOWER(name) LIKE '%вокал%'
    """, (user_id,))
    
    vocal_cats = cursor.fetchall()
    
    if vocal_cats:
        for cat in vocal_cats:
            # Сначала удаляем подкатегории
            cursor.execute("DELETE FROM categories WHERE parent_id = ?", (cat["id"],))
            # Потом удаляем саму категорию
            cursor.execute("DELETE FROM categories WHERE id = ?", (cat["id"],))
            removed.append(f"❌ {cat['name']}")
    else:
        removed.append("⚠️ Вокал не найден")
    
    # ===== 2. ДОБАВЛЯЕМ ПОДКАТЕГОРИИ В "ЕДА" =====
    cursor.execute(
        "SELECT id FROM categories WHERE name = 'Еда' AND user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    food_parent = cursor.fetchone()
    
    if food_parent:
        # Сладости
        cursor.execute(
            "SELECT id FROM categories WHERE name = 'Сладости' AND parent_id = ? AND user_id = ?",
            (food_parent["id"], user_id)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, "Сладости", food_parent["id"])
            )
            added.append("✅ Еда → Сладости")
        
        # Перекус
        cursor.execute(
            "SELECT id FROM categories WHERE name = 'Перекус' AND parent_id = ? AND user_id = ?",
            (food_parent["id"], user_id)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, "Перекус", food_parent["id"])
            )
            added.append("✅ Еда → Перекус")
    else:
        removed.append("⚠️ Категория 'Еда' не найдена")
    
    # ===== 3. СОЗДАЁМ "МЕЛОЧИ" =====
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
        added.append("✅ Создана категория: Мелочи")
    else:
        added.append("⚠️ Мелочи уже существуют")
    
    conn.commit()
    conn.close()
    
    # ===== ОТЧЁТ =====
    text = "🔧 **Обновление категорий завершено!**\n\n"
    
    if removed:
        text += "**Удалено:**\n" + "\n".join(f"• {x}" for x in removed) + "\n\n"
    
    if added:
        text += "**Добавлено:**\n" + "\n".join(f"• {x}" for x in added) + "\n\n"
    
    text += "🔄 **Теперь отправь /start для обновления меню!**"
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("myid"))
async def show_id(message: Message):
    await message.answer(f"Твой ID: {message.from_user.id}")


@router.message(Command("listcategories"))
async def list_categories(message: Message):
    """Показать все категории для отладки"""
    if message.from_user.id != ADMIN_ID:
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
    
    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL ORDER BY id", (user_id,))
    parents = cursor.fetchall()
    
    text = "📂 **Все категории:**\n\n"
    
    for p in parents:
        text += f"📁 **{p['name']}**\n"
        
        cursor.execute("SELECT name FROM categories WHERE parent_id = ? ORDER BY id", (p["id"],))
        children = cursor.fetchall()
        
        for c in children:
            text += f"  • {c['name']}\n"
        
        if not children:
            text += f"  • (нет подкатегорий)\n"
        
        text += "\n"
    
    conn.close()
    
    await message.answer(text, parse_mode="Markdown")
