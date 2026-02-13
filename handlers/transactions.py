from aiogram import Router
from aiogram.types import Message
from database.db import get_connection

router = Router()

@router.message(lambda message: message.text and message.text[0].isdigit())
async def add_transaction(message: Message):
    lines = message.text.split("\n")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()
    user_id = user["id"]

    total_added = 0

    for line in lines:
        parts = line.strip().split(" ", 1)
        if len(parts) < 2:
            continue

        amount = float(parts[0])
        description = parts[1]

        cursor.execute("""
            INSERT INTO transactions (user_id, amount, description, type)
            VALUES (?, ?, ?, ?)
        """, (user_id, amount, description, "expense"))

        total_added += amount

    conn.commit()
    conn.close()

    await message.answer(f"Добавлено расходов на сумму {total_added:.2f}")