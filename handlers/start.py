from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from database.models import create_tables, seed_categories
from database.db import get_connection
from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message):
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    # Добавляем пользователя, если его нет
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )

    conn.commit()

    # Получаем ID пользователя
    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()

    if not user:
        await message.answer("Ошибка создания пользователя.")
        conn.close()
        return

    user_id = user["id"]

    # Автосоздание категорий (если их ещё нет)
    seed_categories(user_id)

    conn.close()

    await message.answer(
        "Бот запущен. Категории созданы.\n\nМожно начинать учёт финансов.",
        reply_markup=main_menu_keyboard()
    )
