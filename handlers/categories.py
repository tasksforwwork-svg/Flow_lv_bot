from aiogram import Router, F
from aiogram.types import Message
from database.db import get_connection

router = Router()


# Когда нажимают кнопку "⚙️ Категории"
@router.message(F.text == "⚙️ Категории")
async def show_categories(message: Message):
    conn = get_connection()
    cursor = conn.cursor()

    # Находим пользователя
    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()

    if not user:
        await message.answer("Пользователь не найден.")
        return

    user_id = user["id"]

    # Получаем список категорий
    cursor.execute(
        "SELECT name FROM categories WHERE user_id = ?",
        (user_id,)
    )
    categories = cursor.fetchall()

    conn.close()

    if not categories:
        await message.answer(
            "Категорий пока нет.\n\n"
            "Напишите название новой категории."
        )
    else:
        text = "Ваши категории:\n\n"
        for cat in categories:
            text += f"• {cat['name']}\n"

        text += "\nНапишите название новой категории."

        await message.answer(text)


# Создание новой категории
@router.message()
async def create_category(message: Message):

    # Игнорируем команды типа /start
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

    # Добавляем новую категорию
    cursor.execute(
        "INSERT INTO categories (user_id, name) VALUES (?, ?)",
        (user_id, message.text.strip())
    )

    conn.commit()
    conn.close()

    await message.answer(f"Категория '{message.text}' добавлена.")