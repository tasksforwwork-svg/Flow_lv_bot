from database.db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Пользователи
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Категории
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        parent_id INTEGER NULL
    )
    """)

    # Транзакции
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        description TEXT,
        category_id INTEGER,
        type TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Бюджеты по категориям
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category_id INTEGER,
        monthly_limit REAL,
        UNIQUE(user_id, category_id)
    )
    """)

    conn.commit()
    conn.close()


def seed_categories(user_id):
    """Создание категорий для НОВЫХ пользователей"""
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем, есть ли уже категории
    cursor.execute(
        "SELECT COUNT(*) as count FROM categories WHERE user_id = ?",
        (user_id,)
    )
    existing = cursor.fetchone()["count"]

    if existing > 0:
        conn.close()
        return  # Категории уже есть, не создаём заново

    # Структура категорий с НОВЫМИ подкатегориями
    structure = {
        "Еда": [
            "Продукты на неделю",
            "Заведения",
            "Обеды в будни",
            "Кофе"  # ✅ ДОБАВЛЕНО
        ],
        "Транспорт": [
            "Такси",
            "Проезд"
        ],
        "Базовый минимум": [
            "Аренда",
            "Коммунальные",
            "Интернет",
            "Телефон"
        ],
        "Здоровье": [
            "Аптека",
            "Врачи"
        ],
        "Спорт": [],
        "Вокал": [],
        "Развлечения": [
            "Кино",
            "Подписки",
            "ЧГК",    # ✅ ДОБАВЛЕНО
            "Квизы"   # ✅ ДОБАВЛЕНО
        ],
        "Одежда": [],
        "Косметика": [],
        "Быт": [],
        "Подарки": [],
        "Импульсные покупки": [],
        "Доход": [
            "Зарплата",
            "Аванс"
        ]
    }

    # Создаём категории
    for parent_name, children in structure.items():
        # Родительская категория
        cursor.execute(
            "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, NULL)",
            (user_id, parent_name)
        )
        parent_id = cursor.lastrowid

        # Подкатегории
        for child in children:
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, child, parent_id)
            )

    conn.commit()
    conn.close()
