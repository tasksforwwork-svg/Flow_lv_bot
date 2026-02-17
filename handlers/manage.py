from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)
router = Router()


class ManageState(StatesGroup):
    waiting_for_edit_action = State()
    waiting_for_new_amount = State()
    waiting_for_new_category = State()
    waiting_for_new_description = State()


# ===== ПОСЛЕДНИЕ ТРАНЗАКЦИИ =====
@router.message(Command("last", "recent"))
async def show_last_transactions(message: Message):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("❌ Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]

    cursor.execute("""
        SELECT t.id, t.amount, t.description, t.date, c.name as category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC
        LIMIT 10
    """, (user_id,))
    
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        await message.answer("📋 У вас пока нет транзакций")
        return

    text = "📋 **Последние операции:**\n\n"
    keyboard = []
    
    for t in transactions:
        date_str = t["date"][:16].replace("T", " ")
        text += f"🔹 **ID {t['id']}** | {t['amount']:.2f} ₽ | {t['category']}\n"
        text += f"   _{t['description']} | {date_str}_\n\n"
        
        keyboard.append([
            InlineKeyboardButton(text=f"✏️ {t['id']}", callback_data=f"edit_{t['id']}"),
            InlineKeyboardButton(text=f"🗑 {t['id']}", callback_data=f"delete_{t['id']}")
        ])

    keyboard.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_transactions")])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )


# ===== КНОПКА РЕДАКТИРОВАНИЯ =====
@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_transaction(callback: types.CallbackQuery, state: FSMContext):
    transaction_id = int(callback.data.split("_")[1])
    logger.info(f" Редактирование транзакции {transaction_id}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await callback.answer("❌ Ошибка", show_alert=True)
        conn.close()
        return
    user_id = user["id"]
    
    cursor.execute("""
        SELECT t.id, t.amount, t.description, c.name as category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.id = ? AND t.user_id = ?
    """, (transaction_id, user_id))
    
    transaction = cursor.fetchone()
    conn.close()
    
    if not transaction:
        await callback.answer(f"❌ Транзакция #{transaction_id} не найдена", show_alert=True)
        return
    
    await state.update_data(
        transaction_id=transaction_id, 
        user_id=user_id,
        old_amount=transaction['amount']
    )
    await state.set_state(ManageState.waiting_for_edit_action)
    
    keyboard = [
        [InlineKeyboardButton(text="💰 Изменить сумму", callback_data="edit_amount")],
        [InlineKeyboardButton(text="📁 Изменить категорию", callback_data="edit_category")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="edit_description")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="close_transactions")]
    ]
    
    await callback.message.edit_text(
        f"✏️ **Редактирование транзакции #{transaction_id}**\n\n"
        f"💰 Сумма: {transaction['amount']:.2f} ₽\n"
        f"📁 Категория: {transaction['category']}\n"
        f"📝 Описание: {transaction['description']}\n\n"
        f"Что изменить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()


# ===== ИЗМЕНИТЬ СУММУ - КНОПКА =====
@router.callback_query(F.data == "edit_amount")
async def edit_amount_start(callback: types.CallbackQuery, state: FSMContext):
    logger.info("✅ Нажата кнопка 'Изменить сумму'")
    
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла. Используйте /last", show_alert=True)
        return
    
    await state.set_state(ManageState.waiting_for_new_amount)
    
    await callback.message.edit_text(
        "💰 **Введите новую сумму**\n\n"
        "Просто отправьте число:\n"
        "Пример: `500`",
        parse_mode="Markdown"
    )
    await callback.answer()


# ===== СОХРАНЕНИЕ НОВОЙ СУММЫ =====
@router.message(ManageState.waiting_for_new_amount)
async def save_new_amount(message: Message, state: FSMContext):
    logger.info(f" Получено сообщение для сохранения суммы: {message.text}")
    
    if not message.text.strip().isdigit():
        await message.answer("❌ Введите только число. Пример: `500`")
        return
    
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    old_amount = data.get("old_amount", "?")
    
    if not transaction_id:
        await message.answer("❌ Ошибка. Начните с /last")
        await state.clear()
        return
    
    new_amount = float(message.text.strip())
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE transactions SET amount = ? WHERE id = ?", 
            (new_amount, transaction_id)
        )
        conn.commit()
        updated = cursor.rowcount
        conn.close()
        
        logger.info(f" Обновлено строк: {updated}")
        
        if updated > 0:
            await message.answer(
                f"✅ **Сумма изменена!**\n\n"
                f"🔹 ID: {transaction_id}\n"
                f"📉 Было: {old_amount} ₽\n"
                f"📈 Стало: {new_amount} ₽"
            )
        else:
            await message.answer("❌ Не обновлено")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


# ===== ИЗМЕНИТЬ КАТЕГОРИЮ =====
@router.callback_query(F.data == "edit_category")
async def edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла", show_alert=True)
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
    categories = cursor.fetchall()
    conn.close()
    
    keyboard = [[InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories]
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="close_transactions")])
    
    await state.set_state(ManageState.waiting_for_new_category)
    
    await callback.message.edit_text(
        "📁 **Выберите категорию:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def save_new_category(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_new_category.state:
        await callback.answer("⏱ Сессия истекла", show_alert=True)
        return
    
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    new_category_id = int(callback.data.split("_")[1])
    
    if not transaction_id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (new_category_id, transaction_id))
        conn.commit()
        conn.close()
        
        await callback.message.edit_text("✅ **Категория изменена!**")
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# ===== ИЗМЕНИТЬ ОПИСАНИЕ =====
@router.callback_query(F.data == "edit_description")
async def edit_description_start(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла", show_alert=True)
        return
    
    await state.set_state(ManageState.waiting_for_new_description)
    
    await callback.message.edit_text(
        "📝 **Введите описание:**\n\nПример: `Обед в кафе`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ManageState.waiting_for_new_description)
async def save_new_description(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_new_description.state:
        return
    
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    new_description = message.text.strip()
    
    if not transaction_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE transactions SET description = ? WHERE id = ?", (new_description, transaction_id))
        conn.commit()
        conn.close()
        
        await message.answer(f"✅ **Описание изменено!**\n\n📝 {new_description}")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


# ===== ЗАКРЫТЬ =====
@router.callback_query(F.data == "close_transactions")
async def callback_close_transactions(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ===== УДАЛИТЬ =====
@router.callback_query(F.data.startswith("delete_"))
async def callback_delete_transaction(callback: types.CallbackQuery):
    transaction_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await callback.answer("❌ Ошибка", show_alert=True)
        conn.close()
        return
    user_id = user["id"]
    
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"🗑 **Транзакция #{transaction_id} удалена!**")
    await callback.answer("✅ Удалено!")
