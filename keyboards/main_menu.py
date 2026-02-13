from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    keyboard = [
        [KeyboardButton(text="➕ Добавить операцию")],
        [KeyboardButton(text="📊 Отчёт за день")],
        [KeyboardButton(text="📅 Отчёт за месяц")],
        [KeyboardButton(text="💰 Остаток бюджета")]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )