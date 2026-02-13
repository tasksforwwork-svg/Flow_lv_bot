def seed_categories(user_id):
    from database.db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

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
