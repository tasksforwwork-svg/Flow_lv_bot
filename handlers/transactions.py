from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database.db import get_connection

router = Router()

# Описываем состояния
class ExpenseState(StatesGroup):
    waiting_for_category = State()
    waiting_for_subcategory = State()

# Шаг 1 — ввод суммы (триггер: число пробел текст)
@router.message(F.text.regexp(r"^\d+\s+.+"))
async def start_transaction(message: Message, state: FSMContext):
    parts = message.text.strip().split(" ", 1)
    amount = float(parts[0])
    description = parts[1]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        await message.answer("Сначала нажмите /start")
        conn.close()
        return

    user_id = user["id"]

    # Сохраняем данные в состояние FSM
    await state.update_data(amount=amount, description=description, user_id=user_id)
    await state.set_state(ExpenseState.waiting_for_category)

    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
    categories = cursor.fetchall()
    conn.close()

    keyboard = [[KeyboardButton(text=cat["name"])] for cat in categories]
    keyboard.append([KeyboardButton(text="❌ Отмена")])

    await message.answer(
        "Выберите категорию:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )

# Шаг 2 — Выбор категории
@router.message(ExpenseState.waiting_for_category)
async def process_category_selection(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    user_id = data["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL AND user_id = ?", (message.text, user_id))
    parent = cursor.fetchone()

    if not parent:
        await message.answer("Такой категории нет. Выберите из списка.")
        conn.close()
        return

    parent_id = parent["id"]

    # Проверка на подкатегории
    cursor.execute("SELECT id, name FROM categories WHERE parent_id = ?", (parent_id,))
    subcategories = cursor.fetchall()

    if not subcategories:
        # Подкатегорий нет, сохраняем сразу
        save_transaction(cursor, data, parent_id)
        conn.commit()
        conn.close()
        await state.clear()
        await message.answer("Расход сохранён.", reply_markup=types.ReplyKeyboardRemove())
        return

    # Есть подкатегории, переходим к следующему шагу
    await state.update_data(parent_id=parent_id)
    await state.set_state(ExpenseState.waiting_for_subcategory)

    keyboard = [[KeyboardButton(text=sub["name"])] for sub in subcategories]
    keyboard.append([KeyboardButton(text="❌ Отмена")])

    await message.answer(
        "Выберите подкатегорию:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )
    conn.close()

# Шаг 3 — Выбор подкатегории
@router.message(ExpenseState.waiting_for_subcategory)
async def process_subcategory_selection(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    user_id = data["user_id"]
    parent_id = data["parent_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id = ?", (message.text, parent_id))
    child = cursor.fetchone()

    if not child:
        await message.answer("Такой подкатегории нет. Выберите из списка.")
        conn.close()
        return

    save_transaction(cursor, data, child["id"])
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("Расход сохранён.", reply_markup=types.ReplyKeyboardRemove())

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
