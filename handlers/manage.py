from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_connection
from datetime import datetime

router = Router()


# ===== ПОСЛЕДНИЕ ТРАНЗАКЦИИ С КНОПКАМИ =====
@router.message(Command("last", "recent"))
async def show_last_transactions(message: Message):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]

    # Последние 10 транзакций
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
        await message.answer("У вас пока нет транзакций.")
        return

    text = "📋 **Последние 10 операций:**\n\n"
    
    keyboard = []
    for t in transactions:
        date_str = t["date"][:16].replace("T", " ")
        text += f"• **ID {t['id']}** | {t['amount']:.2f} ₽ | {t['category']}\n"
        text += f"  _{t['description']} | {date_str}_\n\n"
        
        # Кнопки для каждой транзакции
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


# ===== ОБРАБОТКА НАЖАТИЙ НА КНОПКИ =====
@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_transaction(callback: types.CallbackQuery, state: FSMContext):
    transaction_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await callback.answer("Ошибка пользователя.", show_alert=True)
        conn.close()
        return
    user_id = user["id"]
    
    # Проверяем, что транзакция принадлежит пользователю
    cursor.execute("""
        SELECT t.id, t.amount, t.description, c.name as category
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.id = ? AND t.user_id = ?
    """, (transaction_id, user_id))
    
    transaction = cursor.fetchone()
    conn.close()
    
    if not transaction:
        await callback.answer("Транзакция не найдена.", show_alert=True)
        return
    
    await state.update_data(transaction_id=transaction_id, user_id=user_id)
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


@router.callback_query(F.data.startswith("delete_"))
async def callback_delete_transaction(callback: types.CallbackQuery):
    transaction_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await callback.answer("Ошибка пользователя.", show_alert=True)
        conn.close()
        return
    user_id = user["id"]
    
    # Проверяем принадлежность
    cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    transaction = cursor.fetchone()
    
    if not transaction:
        await callback.answer("Транзакция не найдена.", show_alert=True)
        conn.close()
        return
    
    # Удаляем
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"🗑 **Транзакция #{transaction_id} удалена!**",
        parse_mode="Markdown"
    )
    await callback.answer("Транзакция удалена!")


@router.callback_query(F.data == "close_transactions")
async def callback_close_transactions(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ===== СОСТОЯНИЯ ДЛЯ РЕДАКТИРОВАНИЯ =====
class ManageState(StatesGroup):
    waiting_for_edit_action = State()
    waiting_for_new_amount = State()
    waiting_for_new_category = State()
    waiting_for_new_description = State()


# ===== ВЫБОР ЧТО РЕДАКТИРОВАТЬ =====
@router.callback_query(ManageState.waiting_for_edit_action, F.data == "edit_amount")
async def edit_amount_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ManageState.waiting_for_new_amount)
    await callback.message.edit_text(
        "💰 Введите новую сумму (только число):\n\nПример: `500`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(ManageState.waiting_for_edit_action, F.data == "edit_category")
async def edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
    categories = cursor.fetchall()
    conn.close()
    
    keyboard = [[InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}")] for cat in categories]
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="close_transactions")])
    
    await state.set_state(ManageState.waiting_for_new_category)
    await callback.message.edit_text(
        "📁 Выберите новую категорию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(ManageState.waiting_for_edit_action, F.data == "edit_description")
async def edit_description_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ManageState.waiting_for_new_description)
    await callback.message.edit_text(
        "📝 Введите новое описание:\n\nПример: `Обед в кафе`",
        parse_mode="Markdown"
    )
    await callback.answer()


# ===== СОХРАНЕНИЕ ИЗМЕНЕНИЙ =====
@router.message(ManageState.waiting_for_new_amount, F.text.regexp(r"^\d+$"))
async def save_new_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    new_amount = float(message.text)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amount, transaction_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Сумма обновлена: {new_amount:.2f} ₽")


@router.callback_query(ManageState.waiting_for_new_category, F.data.startswith("cat_"))
async def save_new_category(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    new_category_id = int(callback.data.split("_")[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (new_category_id, transaction_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await callback.message.edit_text("✅ Категория обновлена!")
    await callback.answer()


@router.message(ManageState.waiting_for_new_description)
async def save_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    new_description = message.text.strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE transactions SET description = ? WHERE id = ?", (new_description, transaction_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Описание обновлено: {new_description}")


# ===== ПОИСК ПО ТРАНЗАКЦИЯМ =====
@router.message(Command("find", "search"))
async def search_transactions(message: Message):
    # Получаем поисковый запрос из команды
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "🔍 **Поиск по транзакциям**\n\n"
            "Использование:\n"
            "`/find кофе` — найти все траты со словом 'кофе'\n"
            "`/find 2024-01` — найти траты за январь 2024\n"
            "`/find Еда` — найти все траты в категории 'Еда'\n"
            "`/find >1000` — найти траты больше 1000₽\n"
            "`/find <500` — найти траты меньше 500₽"
        )
        return
    
    search_query = args[1].lower()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]
    
    # Определяем тип поиска
    if search_query.startswith(">"):
        # Поиск по сумме больше
        amount = float(search_query[1:])
        cursor.execute("""
            SELECT t.id, t.amount, t.description, t.date, c.name as category
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.amount > ?
            ORDER BY t.date DESC
            LIMIT 20
        """, (user_id, amount))
        search_type = f"больше {amount}₽"
        
    elif search_query.startswith("<"):
        # Поиск по сумме меньше
        amount = float(search_query[1:])
        cursor.execute("""
            SELECT t.id, t.amount, t.description, t.date, c.name as category
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.amount < ?
            ORDER BY t.date DESC
            LIMIT 20
        """, (user_id, amount))
        search_type = f"меньше {amount}₽"
        
    elif "-" in search_query and len(search_query) == 7:
        # Поиск по месяцу (2024-01)
        cursor.execute("""
            SELECT t.id, t.amount, t.description, t.date, c.name as category
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND strftime('%Y-%m', t.date) = ?
            ORDER BY t.date DESC
            LIMIT 20
        """, (user_id, search_query))
        search_type = f"за {search_query}"
        
    else:
        # Поиск по тексту в описании или категории
        cursor.execute("""
            SELECT t.id, t.amount, t.description, t.date, c.name as category
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND (LOWER(t.description) LIKE ? OR LOWER(c.name) LIKE ?)
            ORDER BY t.date DESC
            LIMIT 20
        """, (user_id, f"%{search_query}%", f"%{search_query}%"))
        search_type = f"по запросу '{search_query}'"
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        await message.answer(f"🔍 Ничего не найдено {search_type}")
        return
    
    text = f"🔍 **Найдено {len(results)} транзакций** {search_type}:\n\n"
    total = 0
    
    for t in results:
        date_str = t["date"][:16].replace("T", " ")
        text += f"• {t['amount']:.2f} ₽ | {t['category']}\n"
        text += f"  _{t['description']} | {date_str}_\n\n"
        total += t["amount"]
    
    text += f"\n💰 **Итого: {total:.2f} ₽**"
    
    await message.answer(text, parse_mode="Markdown")


# ===== КОМАНДА /delete по ID =====
@router.message(Command("delete"))
async def delete_by_id(message: Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "🗑 **Удаление транзакции**\n\n"
            "Использование:\n"
            "`/delete 123` — удалить транзакцию с ID 123\n\n"
            "Чтобы узнать ID, используйте `/last`"
        )
        return
    
    transaction_id = int(args[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]
    
    cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    transaction = cursor.fetchone()
    
    if not transaction:
        await message.answer("Транзакция не найдена или не принадлежит вам.")
        conn.close()
        return
    
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Транзакция #{transaction_id} удалена!")


# ===== КОМАНДА /edit по ID =====
@router.message(Command("edit"))
async def edit_by_id(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "✏️ **Редактирование транзакции**\n\n"
            "Использование:\n"
            "`/edit 123` — редактировать транзакцию с ID 123\n\n"
            "Чтобы узнать ID, используйте `/last`"
        )
        return
    
    transaction_id = int(args[1])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Сначала нажмите /start")
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
        await message.answer("Транзакция не найдена или не принадлежит вам.")
        return
    
    await state.update_data(transaction_id=transaction_id, user_id=user_id)
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