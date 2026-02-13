from aiogram import Router, F
from aiogram.types import Message
from database.db import get_connection

router = Router()

waiting_for_category = set()


@router.message(F.text == "⚙️ Категории")
async def show_categories(message: Message):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()

    if not user:
        await message.answer("Пользователь не найден.")
        return

    user_id = user["id"]

    cursor.execute(
        "SELECT name FROM categories WHERE user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    categories = cursor.fetchall()

    conn.close()

    text = "Ваши категории:\n\n"
    for cat in categories:
        text += f"• {cat['name']}\n"

    text += "\nВведите название новой категории или напишите 'отмена'."

    waiting_for_category.add(message.from_user.id)

    await message.answer(text)


@router.message()
async def create_category(message: Message):

    if message.from_user.id not in waiting_for_category:
        return

    if message.text.lower() == "отмена":
        waiting_for_category.remove(message.from_user.id)
        await message.answer("Создание категории отменено.")
        return

    if message.text.startswith("/"):
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()

    if not user:
        return

    user_id = user["id"]

    cursor.execute(
        "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, NULL)",
        (user_id, message.text.strip())
    )

    conn.commit()
    conn.close()

    waiting_for_category.remove(message.from_user.id)

    await message.answer(f"Категория '{message.text}' добавлена.")
