from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database.db import get_connection

router = Router()

# Временное хранилище состояний
pending_transactions = {}


# Шаг 1 — пользователь вводит сумму
@router.message(F.text.regexp(r"^\d+"))
async def start_transaction(message: Message):
    parts = message.text.strip().split(" ", 1)

    if len(parts) < 2:
        await message.answer("Формат: 200 кофе")
        return

    amount = float(parts[0])
    description = parts[1]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    user = cursor.fetchone()

    if not user:
        await message.answer("Ошибка пользователя.")
        conn.close()
        return

    user_id = user["id"]

    # Сохраняем временно
    pending_transactions[message.from_user.id] = {
        "amount": amount,
        "description": description,
        "user_id": user_id,
        "step": "parent"
    }

    # Получаем родительские категории
    cursor.execute(
        "SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL",
        (user_id,)
    )
    categories = cursor.fetchall()
    conn.close()

    keyboard = [[KeyboardButton(text=cat["name"])] for cat in categories]

    await message.answer(
        "Выберите категорию:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
    )


# Шаг 2 — выбор родительской категории
@router.message()
async def process_category_selection(message: Message):

    if message.from_user.id not in pending_transactions:
        return

    data = pending_transactions[message.from_user.id]

    conn = get_connection()
    cursor = conn.cursor()

    if data["step"] == "parent":

        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND parent_id IS NULL AND user_id = ?",
            (message.text, data["user_id"])
        )
        parent = cursor.fetchone()

        if not parent:
            return

        parent_id = parent["id"]

        # Получаем подкатегории
        cursor.execute(
            "SELECT id, name FROM categories WHERE parent_id = ?",
            (parent_id,)
        )
        subcategories = cursor.fetchall()

        if not subcategories:
            # Если нет подкатегорий — сохраняем сразу
            save_transaction(cursor, data, parent_id)
            conn.commit()
            conn.close()
            del pending_transactions[message.from_user.id]
            await message.answer("Расход сохранён.")
            return

        # Переходим к шагу подкатегорий
        data["step"] = "child"
        data["parent_id"] = parent_id

        keyboard = [[KeyboardButton(text=sub["name"])] for sub in subcategories]

        await message.answer(
            "Выберите подкатегорию:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True
            )
        )

        conn.close()
        return

    elif data["step"] == "child":

        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND parent_id = ?",
            (message.text, data["parent_id"])
        )
        child = cursor.fetchone()

        if not child:
            return

        category_id = child["id"]

        save_transaction(cursor, data, category_id)

        conn.commit()
        conn.close()

        del pending_transactions[message.from_user.id]

        await message.answer("Расход сохранён.")


def save_transaction(cursor, data, category_id):
    cursor.execute("""
        INSERT INTO transactions (user_id, amount, description, category_id, type)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["amount"],
        data["description"],
        category_id,
        "expense"
    ))
