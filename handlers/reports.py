from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from database.db import get_connection
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = Router()


# ===== ОТЧЁТ ЗА МЕСЯЦ =====
@router.message(F.text == "📅 Отчёт за месяц")
@router.message(Command("month", "report"))
async def report_month(message: Message):
    logger.info(f"📅 Отчёт за месяц запрошен пользователем {message.from_user.id}")
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("❌ Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]

    current_month = datetime.now().strftime("%Y-%m")
    last_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")

    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, current_month))
    current_total = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, last_month))
    last_total = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT c.name, SUM(t.amount) as sum
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND strftime('%Y-%m', t.date) = ?
        GROUP BY c.name
        ORDER BY sum DESC
    """, (user_id, current_month))
    current_categories = cursor.fetchall()

    cursor.execute("""
        SELECT c.name, SUM(t.amount) as sum
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND strftime('%Y-%m', t.date) = ?
        GROUP BY c.name
        ORDER BY sum DESC
    """, (user_id, last_month))
    last_categories = {cat["name"]: cat["sum"] for cat in cursor.fetchall()}

    conn.close()

    if last_total > 0:
        change_percent = ((current_total - last_total) / last_total) * 100
        change_sign = "+" if change_percent > 0 else ""
        change_text = f"{change_sign}{change_percent:.1f}%"
    else:
        change_text = "нет данных за прошлый месяц"

    text = f"📅 **Расходы за этот месяц: {current_total:.2f} ₽**\n"
    text += f"📉 За прошлый месяц: {last_total:.2f} ₽\n"
    text += f"📊 **Изменение: {change_text}**\n\n"

    if current_categories:
        text += "**По категориям:**\n"
        for cat in current_categories:
            percent = (cat["sum"] / current_total * 100) if current_total > 0 else 0
            
            last_cat_sum = last_categories.get(cat["name"], 0)
            if last_cat_sum > 0:
                cat_change = ((cat["sum"] - last_cat_sum) / last_cat_sum) * 100
                cat_change_sign = "+" if cat_change > 0 else ""
                cat_change_text = f"({cat_change_sign}{cat_change:.1f}%)"
            else:
                cat_change_text = "(новая)"
            
            text += f"• {cat['name']}: {cat['sum']:.2f} ₽ ({percent:.1f}%) {cat_change_text}\n"
    else:
        text += "Нет расходов за этот месяц."

    await message.answer(text, parse_mode="Markdown")


# ===== ОСТАТОК БЮДЖЕТА =====
@router.message(F.text == "💰 Остаток бюджета")
@router.message(Command("budget_status", "remaining"))
async def budget_remaining(message: Message):
    logger.info(f"💰 Проверка бюджета запрошена пользователем {message.from_user.id}")
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("❌ Сначала нажмите /start")
        conn.close()
        return
    user_id = user["id"]

    current_month = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT b.category_id, b.monthly_limit, c.name,
               COALESCE(SUM(t.amount), 0) as spent
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON t.category_id = c.id 
            AND strftime('%Y-%m', t.date) = ?
        WHERE b.user_id = ?
        GROUP BY b.category_id
    """, (current_month, user_id))
    
    budgets = cursor.fetchall()
    conn.close()

    if not budgets:
        await message.answer(
            "💰 **У вас нет установленных бюджетов**\n\n"
            "Используйте команду:\n"
            "`/budget` — установить бюджет на категорию"
        )
        return

    text = "💰 **Бюджеты на этот месяц:**\n\n"
    alerts = []

    for b in budgets:
        remaining = b["monthly_limit"] - b["spent"]
        percent_spent = (b["spent"] / b["monthly_limit"] * 100) if b["monthly_limit"] > 0 else 0

        text += f"• **{b['name']}**\n"
        text += f"  Потрачено: {b['spent']:.2f} / {b['monthly_limit']:.2f} ₽\n"
        text += f"  Остаток: {remaining:.2f} ₽ ({100 - percent_spent:.1f}%)\n\n"

        if percent_spent >= 100:
            alerts.append(f"🚨 **{b['name']}**: Бюджет превышен на {b['spent'] - b['monthly_limit']:.2f} ₽!")
        elif percent_spent >= 90:
            alerts.append(f"⚠️ **{b['name']}**: Потрачено {percent_spent:.1f}% бюджета!")

    if alerts:
        text += "\n".join(alerts)

    await message.answer(text, parse_mode="Markdown")


# ===== КНОПКА РЕДАКТИРОВАТЬ =====
@router.message(F.text == "✏️ Редактировать")
async def edit_button_handler(message: Message, state: FSMContext):
    from handlers.edit_transaction import edit_transaction
    await edit_transaction(message, state)


# ===== ПОМОЩЬ =====
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📊 **Команды бота:**

💰 **Учёт расходов:**
Просто напишите: `150 кофе` или `500 продукты`

📈 **Отчёты:**
/month или /report - Отчёт за месяц
/budget_status - Проверка бюджетов

⚙️ **Настройки:**
/budget - Установить бюджет на категорию
/edit - Редактировать транзакцию
/addcategories - Добавить новые подкатегории
/removevocal - Удалить категорию Вокал
/help - Эта справка
"""
    await message.answer(help_text, parse_mode="Markdown")
