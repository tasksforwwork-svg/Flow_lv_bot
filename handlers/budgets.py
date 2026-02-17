from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from database.db import get_connection

router = Router()


class BudgetState(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()


@router.message(F.text == "/budget")
async def start_budget_setup(message: Message, state: FSMContext):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        await message.answer("Сначала нажмите /start")
        conn.close()
        return

    user_id = user["id"]

    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
    categories = cursor.fetchall()
    conn.close()

    keyboard = [[types.KeyboardButton(text=cat["name"])] for cat in categories]
    keyboard.append([types.KeyboardButton(text="❌ Отмена")])

    await state.update_data(user_id=user_id)
    await state.set_state(BudgetState.waiting_for_category)

    await message.answer(
        "Выберите категорию для бюджета:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )


@router.message(BudgetState.waiting_for_category)
async def process_budget_category(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    user_id = data["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (message.text, user_id))
    category = cursor.fetchone()

    if not category:
        await message.answer("Такой категории нет. Выберите из списка.")
        conn.close()
        return

    await state.update_data(category_id=category["id"], category_name=message.text)
    await state.set_state(BudgetState.waiting_for_amount)

    conn.close()
    await message.answer(
        "Введите сумму месячного бюджета (только число):\n\nПример: `15000`",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(BudgetState.waiting_for_amount, F.text.regexp(r"^\d+$"))
async def process_budget_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    category_id = data["category_id"]
    category_name = data["category_name"]
    amount = float(message.text)

    conn = get_connection()
    cursor = conn.cursor()

    # Обновляем или создаём бюджет
    cursor.execute("""
        INSERT INTO budgets (user_id, category_id, monthly_limit)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, category_id) DO UPDATE SET monthly_limit = ?
    """, (user_id, category_id, amount, amount))

    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"✅ Бюджет установлен!\n\n"
        f"📁 Категория: {category_name}\n"
        f"💰 Лимит: {amount:.2f} ₽/месяц"
    )


@router.message(BudgetState.waiting_for_amount)
async def invalid_budget_amount(message: Message):
    await message.answer("Пожалуйста, введите только число. Пример: `15000`")