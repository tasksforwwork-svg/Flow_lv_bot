from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard():
    keyboard = [
        [KeyboardButton(text="📅 Отчёт за месяц")],
        [KeyboardButton(text="💰 Остаток бюджета")],
        [KeyboardButton(text="⚙️ Категории")]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
