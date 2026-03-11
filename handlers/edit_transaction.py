from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)
router = Router()


class EditState(StatesGroup):
    waiting_for_action = State()
    waiting_for_amount = State()
    waiting_for_description = State()


# ===== ПОСЛЕДНИЕ ТРАНЗАКЦИИ ДЛЯ РЕДАКТИРОВАНИЯ =====
@router.message(Command("edit"))
async def edit_transaction(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2 or not args[1].strip().isdigit():
        # Показать последние 5 транзакций
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
            LIMIT 5
        """, (user_id,))
        
        transactions = cursor.fetchall()
        conn.close()
        
        if not transactions:
            await message.answer("📋 У вас пока нет транзакций для редактирования")
            return
        
        text = "✏️ **Последние транзакции:**\n\n"
        keyboard = []
        
        for t in transactions:
            text += f"🔹 **ID {t['id']}** | {t['amount']:.2f} ₽ | {t['category']}\n"
            text += f"   _{t['description']}_\n\n"
            keyboard.append([InlineKeyboardButton(text=f"✏️ {t['id']}", callback_data=f"edit_trans_{t['id']}")])
        
        keyboard.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="edit_close")])
        
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        return
    
    # Редактирование по ID
    transaction_id = int(args[1].strip())
    await open_edit_menu(message, state, transaction_id)


async def open_edit_menu(message_or_callback, state, transaction_id, is_callback=False):
    """Открыть меню редактирования транзакции"""
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = None
    if is_callback:
        user_telegram_id = message_or_callback.from_user.id
    else:
        user_telegram_id = message_or_callback.from_user.id
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_telegram_id,))
    user = cursor.fetchone()
    
    if not user:
        if is_callback:
            await message_or_callback.answer("❌ Ошибка пользователя", show_alert=True)
        else:
            await message_or_callback.answer("❌ Сначала нажмите /start")
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
        if is_callback:
            await message_or_callback.answer(f"❌ Транзакция #{transaction_id} не найдена", show_alert=True)
        else:
            await message_or_callback.answer(f"❌ Транзакция #{transaction_id} не найдена")
        return
    
    await state.update_data(
        transaction_id=transaction_id,
        user_id=user_id,
        old_amount=transaction['amount'],
        old_description=transaction['description']
    )
    await state.set_state(EditState.waiting_for_action)
    
    keyboard = [
        [InlineKeyboardButton(text="💰 Изменить сумму", callback_data="edit_amount_btn")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="edit_desc_btn")],
        [InlineKeyboardButton(text="🗑 Удалить транзакцию", callback_data="edit_delete_btn")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_close")]
    ]
    
    text = (f"✏️ **Редактирование #{transaction_id}**\n\n"
            f"💰 Сумма: {transaction['amount']:.2f} ₽\n"
            f"📁 Категория: {transaction['category']}\n"
            f"📝 Описание: {transaction['description']}\n\n"
            f"Что изменить?")
    
    if is_callback:
        await message_or_callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")


# ===== ОБРАБОТКА КНОПОК =====
@router.callback_query(F.data.startswith("edit_trans_"))
async def callback_edit_select(callback: types.CallbackQuery, state: FSMContext):
    transaction_id = int(callback.data.split("_")[2])
    await open_edit_menu(callback, state, transaction_id, is_callback=True)


@router.callback_query(F.data == "edit_amount_btn")
async def callback_edit_amount(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != EditState.waiting_for_action.state:
        await callback.answer("⏱ Сессия истекла. Используйте /edit", show_alert=True)
        return
    
    await state.set_state(EditState.waiting_for_amount)
    await callback.message.edit_text("💰 **Введите новую сумму:**\n\nПример: `500`", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_desc_btn")
async def callback_edit_desc(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != EditState.waiting_for_action.state:
        await callback.answer("⏱ Сессия истекла. Используйте /edit", show_alert=True)
        return
    
    await state.set_state(EditState.waiting_for_description)
    await callback.message.edit_text("📝 **Введите новое описание:**", parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_delete_btn")
async def callback_edit_delete(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    user_id = data.get("user_id")
    
    if not transaction_id or not user_id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await callback.message.edit_text(f"🗑 **Транзакция #{transaction_id} удалена!**", parse_mode="Markdown")
    await callback.answer("✅ Удалено!")


@router.callback_query(F.data == "edit_close")
async def callback_edit_close(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ===== СОХРАНЕНИЕ ИЗМЕНЕНИЙ =====
@router.message(EditState.waiting_for_amount)
async def save_new_amount(message: Message, state: FSMContext):
    if not message.text.strip().replace(",", ".").replace(".", "").isdigit():
        await message.answer("❌ Введите только число. Пример: `500`")
        return
    
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    old_amount = data.get("old_amount", "?")
    
    if not transaction_id:
        await message.answer("❌ Ошибка. Начните с /edit")
        await state.clear()
        return
    
    new_amount = float(message.text.strip().replace(",", "."))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amount, transaction_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ **Сумма изменена!**\n\n📉 Было: {old_amount} ₽\n📈 Стало: {new_amount} ₽", parse_mode="Markdown")


@router.message(EditState.waiting_for_description)
async def save_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    
    if not transaction_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return
    
    new_description = message.text.strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET description = ? WHERE id = ?", (new_description, transaction_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ **Описание изменено!**\n\n📝 {new_description}", parse_mode="Markdown")
