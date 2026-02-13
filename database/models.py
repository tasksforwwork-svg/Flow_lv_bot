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

    # Категории (с поддержкой подкатегорий через parent_id)
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
        monthly_limit REAL
    )
    """)

    conn.commit()
    conn.close()


def seed_categories(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем — вдруг уже созданы
    cursor.execute(
        "SELECT COUNT(*) as count FROM categories WHERE user_id = ?",
        (user_id,)
    )
    existing = cursor.fetchone()["count"]

    if existing > 0:
        conn.close()
        return

    structure = {
        "Еда": [
            "Продукты на неделю",
            "Заведения",
            "Обеды в будни"
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
            "Подписки"
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

    for parent_name, children in structure.items():

        # Создаём родительскую категорию
        cursor.execute(
            "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, NULL)",
            (user_id, parent_name)
        )
        parent_id = cursor.lastrowid

        # Создаём подкатегории
        for child in children:
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                (user_id, child, parent_id)
            )

    conn.commit()
    conn.close()
