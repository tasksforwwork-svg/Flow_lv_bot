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

    # Проверяем, есть ли вообще транзакции
    cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()["count"]
    
    if count == 0:
        await message.answer(
            "📋 **У вас пока нет транзакций**\n\n"
            "Добавьте первую:\n"
            "Пример: `100 Кофе`"
        )
        conn.close()
        return

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

    text = f"📋 **Последние {len(transactions)} операций** (всего: {count}):\n\n"
    
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


# ===== ОБРАБОТКА КНОПКИ РЕДАКТИРОВАНИЯ =====
@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_transaction(callback: types.CallbackQuery, state: FSMContext):
    transaction_id = int(callback.data.split("_")[1])
    
    logger.info(f" Редактирование транзакции {transaction_id} пользователем {callback.from_user.id}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем user_id
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        logger.error(f"Пользователь {callback.from_user.id} не найден в БД")
        await callback.answer("❌ Ошибка: пользователь не найден. Нажмите /start", show_alert=True)
        conn.close()
        return
    
    user_id = user["id"]
    logger.info(f"User ID в БД: {user_id}")
    
    # Проверяем транзакцию
    cursor.execute("""
        SELECT t.id, t.amount, t.description, t.category_id, c.name as category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.id = ? AND t.user_id = ?
    """, (transaction_id, user_id))
    
    transaction = cursor.fetchone()
    
    if not transaction:
        # Дополнительная проверка - существует ли транзакция вообще
        cursor.execute("SELECT user_id FROM transactions WHERE id = ?", (transaction_id,))
        other_transaction = cursor.fetchone()
        
        if other_transaction:
            logger.warning(f"Транзакция {transaction_id} принадлежит другому пользователю (user_id={other_transaction['user_id']})")
            await callback.answer(f"❌ Транзакция #{transaction_id} принадлежит другому пользователю", show_alert=True)
        else:
            logger.warning(f"Транзакция {transaction_id} не существует")
            await callback.answer(f"❌ Транзакция #{transaction_id} не существует", show_alert=True)
        
        conn.close()
        return
    
    logger.info(f"✅ Транзакция найдена: {transaction}")
    
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
        f"Что хотите изменить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()


# ===== ИЗМЕНИТЬ СУММУ =====
@router.callback_query(F.data == "edit_amount")
async def edit_amount_start(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла. Начните сначала через /last", show_alert=True)
        return
    
    await state.set_state(ManageState.waiting_for_new_amount)
    
    await callback.message.edit_text(
        "💰 **Введите новую сумму**\n\n"
        "Отправьте число сообщением:\n"
        "Пример: `500`",
        parse_mode="Markdown"
    )
    await callback.answer()


# ===== СОХРАНЕНИЕ НОВОЙ СУММЫ =====
@router.message(ManageState.waiting_for_new_amount)
async def save_new_amount(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Пожалуйста, введите только число. Пример: `500`")
        return
    
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    
    if not transaction_id:
        await message.answer("❌ Ошибка сессии. Начните сначала через /last")
        await state.clear()
        return
    
    new_amount = float(message.text.strip())
    old_amount = data.get("old_amount", "?")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        logger.info(f"Обновление транзакции {transaction_id}: {old_amount} -> {new_amount}")
        
        cursor.execute(
            "UPDATE transactions SET amount = ? WHERE id = ?", 
            (new_amount, transaction_id)
        )
        conn.commit()
        
        updated = cursor.rowcount
        conn.close()
        
        if updated > 0:
            await message.answer(
                f"✅ **Сумма обновлена!**\n\n"
                f"🔹 Транзакция #{transaction_id}\n"
                f"📉 Было: {old_amount} ₽\n"
                f"📈 Стало: {new_amount} ₽\n\n"
                f"Используйте /last чтобы проверить"
            )
        else:
            await message.answer("❌ Не удалось обновить. Транзакция не найдена.")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении суммы: {e}")
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


# ===== ИЗМЕНИТЬ КАТЕГОРИЮ =====
@router.callback_query(F.data == "edit_category")
async def edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла. Начните сначала через /last", show_alert=True)
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
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
        "📁 **Выберите новую категорию:**",
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
        await callback.answer("❌ Ошибка: транзакция не найдена", show_alert=True)
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE transactions SET category_id = ? WHERE id = ?", 
            (new_category_id, transaction_id)
        )
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(
            f"✅ **Категория обновлена!**\n\n"
            f"Транзакция #{transaction_id} изменена.\n"
            f"Используйте /last чтобы проверить"
        )
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении категории: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


# ===== ИЗМЕНИТЬ ОПИСАНИЕ =====
@router.callback_query(F.data == "edit_description")
async def edit_description_start(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ManageState.waiting_for_edit_action.state:
        await callback.answer("⏱ Сессия истекла. Начните сначала через /last", show_alert=True)
        return
    
    await state.set_state(ManageState.waiting_for_new_description)
    
    await callback.message.edit_text(
        "📝 **Введите новое описание:**\n\n"
        "Пример: `Обед в кафе`",
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
        await message.answer("❌ Ошибка сессии. Начните сначала через /last")
        await state.clear()
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE transactions SET description = ? WHERE id = ?", 
            (new_description, transaction_id)
        )
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ **Описание обновлено!**\n\n"
            f"🔹 Транзакция #{transaction_id}\n"
            f"📝 Новое описание: {new_description}"
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении описания: {e}")
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


# ===== ЗАКРЫТЬ =====
@router.callback_query(F.data == "close_transactions")
async def callback_close_transactions(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ===== УДАЛЕНИЕ =====
@router.callback_query(F.data.startswith("delete_"))
async def callback_delete_transaction(callback: types.CallbackQuery):
    transaction_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        conn.close()
        return
    user_id = user["id"]
    
    cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    transaction = cursor.fetchone()
    
    if not transaction:
        await callback.answer(f"❌ Транзакция #{transaction_id} не найдена", show_alert=True)
        conn.close()
        return
    
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"🗑 **Транзакция #{transaction_id} удалена!**",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Удалено!")


# ===== КОМАНДА /edit =====
@router.message(Command("edit"))
async def edit_by_id(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(
            "✏️ **Редактирование транзакции**\n\n"
            "Использование:\n"
            "`/edit 123` — редактировать транзакцию с ID 123\n\n"
            "💡 **Сначала используйте `/last`** чтобы увидеть ID транзакций!"
        )
        return
    
    transaction_id = int(args[1].strip())
    
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
        SELECT t.id, t.amount, t.description, c.name as category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.id = ? AND t.user_id = ?
    """, (transaction_id, user_id))
    
    transaction = cursor.fetchone()
    
    if not transaction:
        # Показываем какие ID существуют
        cursor.execute("SELECT id FROM transactions WHERE user_id = ? LIMIT 5", (user_id,))
        existing = cursor.fetchall()
        conn.close()
        
        if existing:
            ids = ", ".join(str(t["id"]) for t in existing)
            await message.answer(
                f"❌ **Транзакция #{transaction_id} не найдена**\n\n"
                f"💡 Доступные ID: {ids}\n"
                f"Используйте `/last` чтобы увидеть все"
            )
        else:
            await message.answer(
                "❌ **У вас нет транзакций**\n\n"
                "Добавьте первую:\n"
                "Пример: `100 Кофе`"
            )
        return
    
    conn.close()
    
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
    
    await message.answer(
        f"✏️ **Редактирование транзакции #{transaction_id}**\n\n"
        f"💰 Сумма: {transaction['amount']:.2f} ₽\n"
        f"📁 Категория: {transaction['category']}\n"
        f"📝 Описание: {transaction['description']}\n\n"
        f"Что хотите изменить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
