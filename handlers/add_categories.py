from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_connection

router = Router()

# ✅ ТВОЙ ID:
ADMIN_ID = 534808305


@router.message(Command("addcategories"))
async def add_missing_categories(message: Message):
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
    added = []
    
    # Категории для добавления
    to_add = [
        ("Еда", "Кофе"),
        ("Еда", "Сладости"),
        ("Еда", "Перекус"),
        ("Развлечения", "ЧГК"),
        ("Развлечения", "Квизы")
    ]
    
    for parent_name, child_name in to_add:
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND user_id = ? AND parent_id IS NULL",
            (parent_name, user_id)
        )
        parent = cursor.fetchone()
        
        if not parent:
            continue
        
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND parent_id = ? AND user_id = ?",
            (child_name, parent["id"], user_id)
        )
        if cursor.fetchone():
            continue
        
        cursor.execute(
            "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
            (user_id, child_name, parent["id"])
        )
        added.append(f"{parent_name} → {child_name}")
    
    conn.commit()
    conn.close()
    
    if added:
        await message.answer(f"✅ Добавлено:\n" + "\n".join(f"• {x}" for x in added) + "\n\nТеперь отправь /start")
    else:
        await message.answer("⚠️ Ничего не добавлено (уже существуют)")


@router.message(Command("myid"))
async def show_id(message: Message):
    await message.answer(f"Твой ID: {message.from_user.id}")


@router.message(Command("removevocal"))
async def remove_vocal(message: Message):
    """Удалить категорию Вокал"""
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
    
    # Находим и удаляем категорию "Вокал"
    cursor.execute(
        "DELETE FROM categories WHERE name = 'Вокал' AND user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        await message.answer("✅ Категория **Вокал** удалена!\n\nТеперь отправь /start")
    else:
        await message.answer("⚠️ Категория **Вокал** не найдена")
