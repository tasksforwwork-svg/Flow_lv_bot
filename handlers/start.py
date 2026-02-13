from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.models import create_tables
from database.db import get_connection
from keyboards.main_menu import main_menu_keyboard

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        "Бот запущен. Начинаем учёт финансов.",
        reply_markup=main_menu_keyboard()
    )