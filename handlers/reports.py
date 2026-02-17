from aiogram import Router, F
from aiogram.types import Message
from database.db import get_connection
from datetime import datetime, timedelta

router = Router()

@router.message(F.text == "📊 Отчёт за день")
async def report_day(message: Message):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        return
    user_id = user["id"]

    today = datetime.now().date()
    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE user_id = ? AND date(date) = date(?)
    """, (user_id, today))
    
    res = cursor.fetchone()[0]
    total = res if res else 0.0
    conn.close()
    
    await message.answer(f"💰 Расходы за сегодня: {total} руб.")

@router.message(F.text == "📅 Отчёт за месяц")
async def report_month(message: Message):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        return
    user_id = user["id"]

    # Простой запрос за текущий месяц
    cursor.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
    """, (user_id,))
    
    res = cursor.fetchone()[0]
    total = res if res else 0.0
    conn.close()
    
    await message.answer(f"📅 Расходы за этот месяц: {total} руб.")

# Заглушки для остальных кнопок, чтобы бот не молчал
@router.message(F.text == "💰 Остаток бюджета")
async def budget_remaining(message: Message):
    await message.answer("Функция в разработке. Нужно установить лиметы в настройках.")

@router.message(F.text == "➕ Добавить операцию")
async def add_operation_hint(message: Message):
    await message.answer("Напишите сумму и название, например: 500 Продукты")