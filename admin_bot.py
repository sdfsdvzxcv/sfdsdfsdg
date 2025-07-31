import asyncio
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Инициализация админ-бота
admin_bot = Bot(token=os.getenv('ADMIN_BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM для админ-панели
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_media = State()
    waiting_for_poem_title = State()
    waiting_for_poem_content = State()
    waiting_for_author_name = State()
    waiting_for_author_country = State()
    waiting_for_author_period = State()

# Список админов (можно вынести в базу данных)
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Клавиатуры для админ-панели
def get_admin_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Управление стихами", callback_data="admin_poems")],
        [InlineKeyboardButton(text="👤 Управление авторами", callback_data="admin_authors")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📋 Предложения пользователей", callback_data="admin_submissions")],
        [InlineKeyboardButton(text="➕ Добавить стихотворение", callback_data="admin_add_poem")]
    ])
    return keyboard

def get_poem_management_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Все стихи", callback_data="admin_all_poems")],
        [InlineKeyboardButton(text="🔍 Поиск стихов", callback_data="admin_search_poems")],
        [InlineKeyboardButton(text="🗑️ Удалить стих", callback_data="admin_delete_poem")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
    ])
    return keyboard

def get_author_management_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Все авторы", callback_data="admin_all_authors")],
        [InlineKeyboardButton(text="➕ Добавить автора", callback_data="admin_add_author")],
        [InlineKeyboardButton(text="🗑️ Удалить автора", callback_data="admin_delete_author")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
    ])
    return keyboard

def get_broadcast_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текстовое сообщение", callback_data="admin_broadcast_text")],
        [InlineKeyboardButton(text="🖼️ Фото", callback_data="admin_broadcast_photo")],
        [InlineKeyboardButton(text="🎥 Видео", callback_data="admin_broadcast_video")],
        [InlineKeyboardButton(text="🎬 GIF", callback_data="admin_broadcast_gif")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
    ])
    return keyboard

# Обработчики команд
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard()
    )

# Обработчики callback для админ-панели
@dp.callback_query(lambda c: c.data == "admin_main")
async def admin_main_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Статистика пользователей
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Статистика стихов
    cursor.execute('SELECT COUNT(*) FROM poems')
    total_poems = cursor.fetchone()[0]
    
    # Статистика авторов
    cursor.execute('SELECT COUNT(*) FROM authors')
    total_authors = cursor.fetchone()[0]
    
    # Статистика предложений
    cursor.execute('SELECT COUNT(*) FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 Статистика проекта:

👥 Пользователей: {total_users}
📖 Стихотворений: {total_poems}
👤 Авторов: {total_authors}
📋 Ожидающих предложений: {pending_submissions}
    """
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
        ])
    )

@dp.callback_query(lambda c: c.data == "admin_poems")
async def admin_poems_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "📝 Управление стихотворениями\n\nВыберите действие:",
        reply_markup=get_poem_management_keyboard()
    )

@dp.callback_query(lambda c: c.data == "admin_all_poems")
async def admin_all_poems(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, a.name, p.created_at 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY p.created_at DESC 
        LIMIT 20
    ''')
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        text = "📖 Последние стихотворения:\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for poem_id, title, author, created_at in poems:
            author_text = f" - {author}" if author else ""
            text += f"• {title}{author_text}\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"👁️ {title}", callback_data=f"admin_view_poem_{poem_id}")
            ])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_poems")])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "📚 Стихотворений пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_poems")]
            ])
        )

@dp.callback_query(lambda c: c.data == "admin_authors")
async def admin_authors_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "👤 Управление авторами\n\nВыберите действие:",
        reply_markup=get_author_management_keyboard()
    )

@dp.callback_query(lambda c: c.data == "admin_all_authors")
async def admin_all_authors(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, country, period FROM authors ORDER BY name')
    authors = cursor.fetchall()
    conn.close()
    
    if authors:
        text = "👤 Все авторы:\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for author_id, name, country, period in authors:
            country_text = f" ({country})" if country else ""
            period_text = f" [{period}]" if period else ""
            text += f"• {name}{country_text}{period_text}\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=name, callback_data=f"admin_view_author_{author_id}")
            ])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_authors")])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "👤 Авторов пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_authors")]
            ])
        )

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "📨 Рассылка\n\nВыберите тип сообщения:",
        reply_markup=get_broadcast_keyboard()
    )

@dp.callback_query(lambda c: c.data == "admin_broadcast_text")
async def admin_broadcast_text_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "📝 Введите текст для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    
    await state.set_state(AdminStates.waiting_for_broadcast_text)

@dp.message(AdminStates.waiting_for_broadcast_text)
async def admin_broadcast_text_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    text = message.text
    
    # Получаем всех пользователей
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    # Отправляем сообщение всем пользователям
    success_count = 0
    error_count = 0
    
    for (user_id,) in users:
        try:
            await admin_bot.send_message(user_id, text)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"Error sending to {user_id}: {e}")
    
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок: {error_count}",
        reply_markup=get_admin_main_keyboard()
    )
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast_photo")
async def admin_broadcast_photo_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await callback.message.edit_text(
        "🖼️ Отправьте фото для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
        ])
    )
    
    await state.set_state(AdminStates.waiting_for_broadcast_media)

@dp.message(AdminStates.waiting_for_broadcast_media)
async def admin_broadcast_media_process(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    # Получаем всех пользователей
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    success_count = 0
    error_count = 0
    
    # Отправляем медиа всем пользователям
    for (user_id,) in users:
        try:
            if message.photo:
                await admin_bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await admin_bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.animation:
                await admin_bot.send_animation(user_id, message.animation.file_id, caption=message.caption)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"Error sending media to {user_id}: {e}")
    
    await message.answer(
        f"✅ Рассылка медиа завершена!\n\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок: {error_count}",
        reply_markup=get_admin_main_keyboard()
    )
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_submissions")
async def admin_submissions(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.id, us.content, u.username, u.first_name, us.created_at 
        FROM user_submissions us 
        JOIN users u ON us.user_id = u.user_id 
        WHERE us.status = 'pending' 
        ORDER BY us.created_at DESC
    ''')
    
    submissions = cursor.fetchall()
    conn.close()
    
    if submissions:
        text = "📋 Предложения пользователей:\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for submission_id, content, username, first_name, created_at in submissions:
            user_text = username or first_name or "Пользователь"
            preview = content[:50] + "..." if len(content) > 50 else content
            text += f"• {user_text}: {preview}\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"👁️ {preview}", callback_data=f"admin_view_submission_{submission_id}")
            ])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "📋 Предложений пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")]
            ])
        )

@dp.callback_query(lambda c: c.data.startswith("admin_view_submission_"))
async def admin_view_submission(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    submission_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.content, u.username, u.first_name, us.created_at 
        FROM user_submissions us 
        JOIN users u ON us.user_id = u.user_id 
        WHERE us.id = ?
    ''', (submission_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        content, username, first_name, created_at = result
        user_text = username or first_name or "Пользователь"
        
        text = f"📋 Предложение от {user_text}:\n\n{content}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_submission_{submission_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_submission_{submission_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_submissions")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("admin_approve_submission_"))
async def admin_approve_submission(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    submission_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Получаем данные предложения
    cursor.execute('SELECT user_id, content FROM user_submissions WHERE id = ?', (submission_id,))
    result = cursor.fetchone()
    
    if result:
        user_id, content = result
        
        # Обновляем статус предложения
        cursor.execute('UPDATE user_submissions SET status = "approved" WHERE id = ?', (submission_id,))
        
        # Добавляем стихотворение (можно добавить логику для извлечения автора и названия)
        cursor.execute('''
            INSERT INTO poems (title, content, author_id) 
            VALUES (?, ?, NULL)
        ''', ("Предложенное стихотворение", content))
        
        conn.commit()
        conn.close()
        
        # Уведомляем пользователя
        try:
            await admin_bot.send_message(user_id, "✅ Ваше стихотворение было одобрено и добавлено в библиотеку!")
        except Exception as e:
            print(f"Error notifying user {user_id}: {e}")
        
        await callback.message.edit_text(
            "✅ Предложение одобрено и добавлено в библиотеку!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_submissions")]
            ])
        )
    else:
        conn.close()
        await callback.answer("❌ Предложение не найдено!")

@dp.callback_query(lambda c: c.data.startswith("admin_reject_submission_"))
async def admin_reject_submission(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    submission_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Получаем данные предложения
    cursor.execute('SELECT user_id FROM user_submissions WHERE id = ?', (submission_id,))
    result = cursor.fetchone()
    
    if result:
        user_id = result[0]
        
        # Обновляем статус предложения
        cursor.execute('UPDATE user_submissions SET status = "rejected" WHERE id = ?', (submission_id,))
        conn.commit()
        conn.close()
        
        # Уведомляем пользователя
        try:
            await admin_bot.send_message(user_id, "❌ К сожалению, ваше стихотворение не было одобрено.")
        except Exception as e:
            print(f"Error notifying user {user_id}: {e}")
        
        await callback.message.edit_text(
            "❌ Предложение отклонено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_submissions")]
            ])
        )
    else:
        conn.close()
        await callback.answer("❌ Предложение не найдено!")

# Запуск админ-бота
async def main():
    await dp.start_polling(admin_bot)

if __name__ == "__main__":
    asyncio.run(main())