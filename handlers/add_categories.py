from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)
router = Router()

# ✅ ТВОЙ ID:
ADMIN_ID = 534808305


@router.message(Command("fixcategories"))
async def fix_all_categories(message: Message):
    """Исправление категорий с подробной отладкой"""
    
    logger.info(f"=== НАЧАЛО ОБНОВЛЕНИЯ КАТЕГОРИЙ ===")
    logger.info(f"User ID: {message.from_user.id}")
    
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещён")
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверка подключения к БД
        logger.info("✅ Подключение к БД успешно")
        
        # Получаем user_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
        user = cursor.fetchone()
        
        if not user:
            logger.error("❌ Пользователь не найден в БД")
            await message.answer("❌ Пользователь не найден в базе")
            conn.close()
            return
        
        user_id = user["id"]
        logger.info(f"✅ User ID в БД: {user_id}")
        
        added = []
        removed = []
        
        # ===== 1. ПОКАЗЫВАЕМ ВСЕ КАТЕГОРИИ ПЕРЕД ИЗМЕНЕНИЯМИ =====
        cursor.execute("SELECT name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
        all_cats = cursor.fetchall()
        cat_names = [c["name"] for c in all_cats]
        logger.info(f"📋 Текущие категории: {cat_names}")
        
        # ===== 2. УДАЛЯЕМ "ВОКАЛ" =====
        cursor.execute("""
            SELECT id, name FROM categories 
            WHERE user_id = ? AND parent_id IS NULL 
            AND LOWER(name) LIKE '%вокал%'
        """, (user_id,))
        
        vocal_cats = cursor.fetchall()
        logger.info(f"🔍 Найдено категорий 'Вокал': {len(vocal_cats)}")
        
        if vocal_cats:
            for cat in vocal_cats:
                cursor.execute("DELETE FROM categories WHERE parent_id = ?", (cat["id"],))
                cursor.execute("DELETE FROM categories WHERE id = ?", (cat["id"],))
                removed.append(f"❌ {cat['name']}")
                logger.info(f"✅ Удалена категория: {cat['name']}")
        else:
            removed.append("⚠️ Вокал не найден")
            logger.warning("⚠️ Вокал не найден в БД")
        
        # ===== 3. ДОБАВЛЯЕМ ПОДКАТЕГОРИИ В "ЕДА" =====
        cursor.execute(
            "SELECT id FROM categories WHERE name = 'Еда' AND user_id = ? AND parent_id IS NULL",
            (user_id,)
        )
        food_parent = cursor.fetchone()
        logger.info(f"🔍 Категория 'Еда': {food_parent}")
        
        if food_parent:
            food_parent_id = food_parent["id"]
            
            # Сладости
            cursor.execute(
                "SELECT id FROM categories WHERE name = 'Сладости' AND parent_id = ? AND user_id = ?",
                (food_parent_id, user_id)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                    (user_id, "Сладости", food_parent_id)
                )
                added.append("✅ Еда → Сладости")
                logger.info("✅ Добавлено: Еда → Сладости")
            else:
                logger.info("⚠️ Сладости уже существуют")
            
            # Перекус
            cursor.execute(
                "SELECT id FROM categories WHERE name = 'Перекус' AND parent_id = ? AND user_id = ?",
                (food_parent_id, user_id)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, ?)",
                    (user_id, "Перекус", food_parent_id)
                )
                added.append("✅ Еда → Перекус")
                logger.info("✅ Добавлено: Еда → Перекус")
            else:
                logger.info("⚠️ Перекус уже существует")
        else:
            removed.append("⚠️ Категория 'Еда' не найдена")
            logger.error("❌ Категория 'Еда' не найдена!")
        
        # ===== 4. СОЗДАЁМ "МЕЛОЧИ" =====
        cursor.execute(
            "SELECT id FROM categories WHERE name = 'Мелочи' AND user_id = ? AND parent_id IS NULL",
            (user_id,)
        )
        misc_parent = cursor.fetchone()
        logger.info(f"🔍 Категория 'Мелочи': {misc_parent}")
        
        if not misc_parent:
            cursor.execute(
                "INSERT INTO categories (user_id, name, parent_id) VALUES (?, ?, NULL)",
                (user_id, "Мелочи")
            )
            added.append("✅ Создана категория: Мелочи")
            logger.info("✅ Создана категория: Мелочи")
        else:
            added.append("⚠️ Мелочи уже существуют")
            logger.info("⚠️ Мелочи уже существуют")
        
        # ===== 5. СОХРАНЯЕМ ИЗМЕНЕНИЯ =====
        conn.commit()
        logger.info("✅ Изменения сохранены в БД")
        
        # ===== 6. ПРОВЕРЯЕМ РЕЗУЛЬТАТ =====
        cursor.execute("SELECT name FROM categories WHERE user_id = ? AND parent_id IS NULL", (user_id,))
        final_cats = cursor.fetchall()
        final_cat_names = [c["name"] for c in final_cats]
        logger.info(f"📋 Итоговые категории: {final_cat_names}")
        
        conn.close()
        logger.info("=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО ===")
        
        # ===== ОТЧЁТ ПОЛЬЗОВАТЕЛЮ =====
        text = "🔧 **Обновление категорий завершено!**\n\n"
        
        if removed:
            text += "**Удалено:**\n" + "\n".join(f"• {x}" for x in removed) + "\n\n"
        
        if added:
            text += "**Добавлено:**\n" + "\n".join(f"• {x}" for x in added) + "\n\n"
        
        text += f"📋 **Все категории:** {', '.join(final_cat_names)}\n\n"
        text += "🔄 **Теперь отправь /start для обновления меню!**"
        
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        await message.answer(f"❌ Произошла ошибка:\n\n`{e}`", parse_mode="Markdown")


@router.message(Command("myid"))
async def show_id(message: Message):
    await message.answer(f"Твой ID: {message.from_user.id}")


@router.message(Command("listcategories"))
async def list_categories(message: Message):
    """Показать все категории для отладки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
        user = cursor.fetchone()
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            conn.close()
            return
        
        user_id = user["id"]
        
        cursor.execute("SELECT id, name FROM categories WHERE user_id = ? AND parent_id IS NULL ORDER BY id", (user_id,))
        parents = cursor.fetchall()
        
        text = "📂 **Все категории:**\n\n"
        
        for p in parents:
            text += f"📁 **{p['name']}** (ID: {p['id']})\n"
            
            cursor.execute("SELECT id, name FROM categories WHERE parent_id = ? ORDER BY id", (p["id"],))
            children = cursor.fetchall()
            
            for c in children:
                text += f"  • {c['name']} (ID: {c['id']})\n"
            
            if not children:
                text += f"  • (нет подкатегорий)\n"
            
            text += "\n"
        
        conn.close()
        
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
