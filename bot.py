import asyncio
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import aiofiles

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot token from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',')  # List of admin IDs

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM States
class PoemStates(StatesGroup):
    waiting_for_poem_text = State()
    waiting_for_author_name = State()
    waiting_for_author_country = State()
    waiting_for_author_period = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_photo = State()
    waiting_for_broadcast_video = State()
    waiting_for_broadcast_gif = State()
    waiting_for_poem_title = State()
    waiting_for_poem_text = State()
    waiting_for_poem_author = State()
    waiting_for_poem_genre = State()
    waiting_for_author_name = State()
    waiting_for_author_country = State()
    waiting_for_author_period = State()

# Database initialization
def init_db():
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Authors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            period TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Poems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            author_id INTEGER,
            genre TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES authors (id)
        )
    ''')
    
    # User library table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poem_id INTEGER,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
        )
    ''')
    
    # User quotes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poem_id INTEGER,
            quote_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
        )
    ''')
    
    # User submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # User notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            frequency TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper functions
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Получить стихотворение", callback_data="get_random_poem")],
        [InlineKeyboardButton(text="🔍 Выбрать стихотворение", callback_data="choose_poem")],
        [InlineKeyboardButton(text="📚 Личная библиотека", callback_data="personal_library")],
        [InlineKeyboardButton(text="➕ Добавить стихотворение", callback_data="add_poem")]
    ])
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Управление стихами", callback_data="admin_poems")],
        [InlineKeyboardButton(text="👤 Управление авторами", callback_data="admin_authors")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📨 Модерация", callback_data="admin_submissions")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_poem_actions_keyboard(poem_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить", callback_data=f"save_poem_{poem_id}")],
        [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem_id}")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")],
        [InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_poem")],
        [InlineKeyboardButton(text="➡️ Следующее", callback_data="next_poem")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_notification_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневно", callback_data="notify_daily")],
        [InlineKeyboardButton(text="📅 Раз в 2 дня", callback_data="notify_2days")],
        [InlineKeyboardButton(text="📅 Раз в 4 дня", callback_data="notify_4days")],
        [InlineKeyboardButton(text="📅 Еженедельно", callback_data="notify_weekly")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="get_random_poem")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_choose_poem_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 По автору", callback_data="by_author")],
        [InlineKeyboardButton(text="🌍 По стране", callback_data="by_country")],
        [InlineKeyboardButton(text="⏰ По периоду", callback_data="by_period")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

# Command handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Register user in database
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()
    
    welcome_text = f"""
🎭 Добро пожаловать в проект «Рильке»!

Маленький мостик к большой поэзии. Пара кликов – и стихотворение уже на вашем экране, новое и случайное или искомое и давно любимое.

Выберите действие:
    """
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📖 **Как пользоваться ботом:**

🎯 **Получить стихотворение** - случайное стихотворение из библиотеки
🔍 **Выбрать стихотворение** - поиск по автору, стране или периоду
📚 **Личная библиотека** - ваши сохраненные стихи
➕ **Добавить стихотворение** - предложить новое стихотворение

💡 **Дополнительные возможности:**
• Сохранение понравившихся стихов
• Настройка регулярных уведомлений
• Поиск по различным критериям
• Поделиться стихотворением с друзьями

/admin - панель администратора (только для админов)
    """
    await message.answer(help_text, reply_markup=get_main_keyboard())

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    
    await message.answer("🔧 Панель администратора", reply_markup=get_admin_keyboard())

# Callback handlers
@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎭 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "get_random_poem")
async def get_random_poem(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Get random poem with author info
    cursor.execute('''
        SELECT p.id, p.title, p.text, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY RANDOM() 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        poem_id, title, text, author_name = result
        author_text = f"Автор: {author_name}" if author_name else "Автор: Неизвестен"
        
        poem_text = f"📖 **{title}**\n\n{author_text}\n\n{text}"
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=get_poem_actions_keyboard(poem_id)
        )
    else:
        await callback.message.edit_text(
            "📚 В библиотеке пока нет стихотворений.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(F.data == "choose_poem")
async def choose_poem(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔍 Выберите способ поиска стихотворения:",
        reply_markup=get_choose_poem_keyboard()
    )

@dp.callback_query(F.data == "by_author")
async def by_author(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name FROM authors ORDER BY name')
    authors = cursor.fetchall()
    conn.close()
    
    if authors:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for author_id, name in authors:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=f"author_{author_id}")])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="choose_poem")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "👤 Выберите автора:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📚 Авторы не найдены.",
            reply_markup=get_choose_poem_keyboard()
        )

@dp.callback_query(F.data.startswith("author_"))
async def author_selected(callback: types.CallbackQuery):
    author_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title FROM poems WHERE author_id = ? ORDER BY title', (author_id,))
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for poem_id, title in poems:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=title, callback_data=f"poem_{poem_id}")])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="by_author")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "📖 Выберите стихотворение:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📚 Стихотворения этого автора не найдены.",
            reply_markup=get_choose_poem_keyboard()
        )

@dp.callback_query(F.data.startswith("poem_"))
async def poem_selected(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.text, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, text, author_name = result
        author_text = f"Автор: {author_name}" if author_name else "Автор: Неизвестен"
        
        poem_text = f"📖 **{title}**\n\n{author_text}\n\n{text}"
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=get_poem_actions_keyboard(poem_id)
        )
    else:
        await callback.message.edit_text(
            "❌ Стихотворение не найдено.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(F.data.startswith("save_poem_"))
async def save_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Check if already saved
    cursor.execute('SELECT id FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    existing = cursor.fetchone()
    
    if not existing:
        cursor.execute('INSERT INTO user_library (user_id, poem_id) VALUES (?, ?)', (user_id, poem_id))
        conn.commit()
        await callback.answer("✅ Стихотворение сохранено в библиотеку!")
    else:
        await callback.answer("📚 Стихотворение уже в библиотеке!")
    
    conn.close()

@dp.callback_query(F.data.startswith("share_poem_"))
async def share_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.text, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, text, author_name = result
        author_text = f"Автор: {author_name}" if author_name else "Автор: Неизвестен"
        
        share_text = f"📖 {title}\n\n{author_text}\n\n{text}\n\n💫 Поделено через @rilke_poetry_bot"
        
        await callback.message.answer(share_text)
        await callback.answer("📤 Стихотворение отправлено в чат!")

@dp.callback_query(F.data == "notifications")
async def notifications(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔔 Настройка уведомлений\n\nВыберите частоту получения случайных стихотворений:",
        reply_markup=get_notification_keyboard()
    )

@dp.callback_query(F.data.startswith("notify_"))
async def set_notification(callback: types.CallbackQuery):
    frequency = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    frequency_map = {
        "daily": "daily",
        "2days": "2days", 
        "4days": "4days",
        "weekly": "weekly"
    }
    
    if frequency in frequency_map:
        conn = sqlite3.connect('poetry.db')
        cursor = conn.cursor()
        
        # Update or insert notification setting
        cursor.execute('''
            INSERT OR REPLACE INTO user_notifications (user_id, frequency, is_active) 
            VALUES (?, ?, 1)
        ''', (user_id, frequency_map[frequency]))
        
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(
            "✅ Ваш выбор сохранён! Вы будете получать стихотворения согласно выбранному расписанию.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(F.data == "personal_library")
async def personal_library(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, a.name 
        FROM user_library ul
        JOIN poems p ON ul.poem_id = p.id
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE ul.user_id = ?
        ORDER BY ul.saved_at DESC
    ''', (user_id,))
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for poem_id, title, author_name in poems:
            author_text = f" ({author_name})" if author_name else ""
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"{title}{author_text}", callback_data=f"lib_poem_{poem_id}")])
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            f"📚 Ваша личная библиотека ({len(poems)} стихотворений):",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📚 Ваша библиотека пуста. Сохраните понравившиеся стихотворения!",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(F.data.startswith("lib_poem_"))
async def lib_poem_selected(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.text, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, text, author_name = result
        author_text = f"Автор: {author_name}" if author_name else "Автор: Неизвестен"
        
        poem_text = f"📖 **{title}**\n\n{author_text}\n\n{text}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить из библиотеки", callback_data=f"remove_from_lib_{poem_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="personal_library")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=keyboard
        )

@dp.callback_query(F.data.startswith("remove_from_lib_"))
async def remove_from_library(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    conn.commit()
    conn.close()
    
    await callback.answer("🗑️ Стихотворение удалено из библиотеки!")
    await personal_library(callback)

@dp.callback_query(F.data == "add_poem")
async def add_poem_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📝 Добавить стихотворение\n\nНапишите текст стихотворения, которое хотите предложить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
    )
    await PoemStates.waiting_for_poem_text.set()

@dp.message(PoemStates.waiting_for_poem_text)
async def add_poem_text(message: types.Message, state: FSMContext):
    await state.update_data(poem_text=message.text)
    
    # Send to admins for moderation
    user_info = f"От пользователя: {message.from_user.first_name} (@{message.from_user.username})"
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_submissions (user_id, text) VALUES (?, ?)', (message.from_user.id, message.text))
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        if admin_id.strip():
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_submission_{submission_id}")],
                    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_submission_{submission_id}")]
                ])
                
                await bot.send_message(
                    admin_id,
                    f"📨 Новое предложение стихотворения\n\n{user_info}\n\nТекст:\n{message.text}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Failed to send to admin {admin_id}: {e}")
    
    await message.answer(
        "✅ Ваше предложение отправлено на модерацию! Мы рассмотрим его в ближайшее время.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# Admin callback handlers
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM users')
    users_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM poems')
    poems_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM authors')
    authors_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 **Статистика проекта**

👥 Пользователей: {users_count}
📖 Стихотворений: {poems_count}
👤 Авторов: {authors_count}
📨 Ожидают модерации: {pending_submissions}
    """
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "admin_poems")
async def admin_poems(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY p.created_at DESC 
        LIMIT 10
    ''')
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        text = "📝 Последние стихотворения:\n\n"
        for poem_id, title, author_name in poems:
            author_text = f" ({author_name})" if author_name else ""
            text += f"• {title}{author_text}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить стихотворение", callback_data="admin_add_poem")],
            [InlineKeyboardButton(text="📋 Все стихотворения", callback_data="admin_all_poems")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "📚 Стихотворений пока нет.",
            reply_markup=get_admin_keyboard()
        )

@dp.callback_query(F.data == "admin_add_poem")
async def admin_add_poem_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📝 Добавить новое стихотворение\n\nВведите название стихотворения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_poems")]
        ])
    )
    await AdminStates.waiting_for_poem_title.set()

@dp.message(AdminStates.waiting_for_poem_title)
async def admin_poem_title(message: types.Message, state: FSMContext):
    await state.update_data(poem_title=message.text)
    await message.answer("Введите текст стихотворения:")
    await AdminStates.waiting_for_poem_text.set()

@dp.message(AdminStates.waiting_for_poem_text)
async def admin_poem_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    poem_title = data['poem_title']
    poem_text = message.text
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO poems (title, text) VALUES (?, ?)', (poem_title, poem_text))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ Стихотворение '{poem_title}' добавлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текстовое сообщение", callback_data="admin_broadcast_text")],
        [InlineKeyboardButton(text="🖼️ Фото", callback_data="admin_broadcast_photo")],
        [InlineKeyboardButton(text="🎥 Видео", callback_data="admin_broadcast_video")],
        [InlineKeyboardButton(text="🎬 GIF", callback_data="admin_broadcast_gif")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]
    ])
    
    await callback.message.edit_text(
        "📢 Рассылка\n\nВыберите тип сообщения:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "admin_broadcast_text")
async def admin_broadcast_text_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📝 Введите текст для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_broadcast")]
        ])
    )
    await AdminStates.waiting_for_broadcast_text.set()

@dp.message(AdminStates.waiting_for_broadcast_text)
async def admin_broadcast_text_send(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    for user_id, in users:
        try:
            await bot.send_message(user_id, f"📢 **Рассылка от администрации:**\n\n{message.text}")
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to {user_id}: {e}")
    
    await message.answer(
        f"✅ Рассылка отправлена {sent_count} пользователям!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_submissions")
async def admin_submissions(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.id, us.text, u.first_name, u.username, us.created_at
        FROM user_submissions us
        JOIN users u ON us.user_id = u.id
        WHERE us.status = 'pending'
        ORDER BY us.created_at DESC
    ''')
    
    submissions = cursor.fetchall()
    conn.close()
    
    if submissions:
        text = "📨 Предложения на модерации:\n\n"
        for submission_id, text_content, first_name, username, created_at in submissions:
            username_text = f"@{username}" if username else "без username"
            text += f"**ID {submission_id}** от {first_name} ({username_text})\n"
            text += f"📅 {created_at}\n"
            text += f"📝 {text_content[:100]}...\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "📨 Предложений на модерации нет.",
            reply_markup=get_admin_keyboard()
        )

@dp.callback_query(F.data.startswith("admin_approve_submission_"))
async def admin_approve_submission(callback: types.CallbackQuery):
    submission_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE user_submissions SET status = "approved" WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "✅ Предложение одобрено!",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data.startswith("admin_reject_submission_"))
async def admin_reject_submission(callback: types.CallbackQuery):
    submission_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE user_submissions SET status = "rejected" WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "❌ Предложение отклонено!",
        reply_markup=get_admin_keyboard()
    )

# Notification sending function
async def send_notifications():
    while True:
        try:
            conn = sqlite3.connect('poetry.db')
            cursor = conn.cursor()
            
            # Get users with active notifications
            cursor.execute('''
                SELECT DISTINCT un.user_id, un.frequency
                FROM user_notifications un
                WHERE un.is_active = 1
            ''')
            
            users = cursor.fetchall()
            
            for user_id, frequency in users:
                # Get random poem
                cursor.execute('''
                    SELECT p.id, p.title, p.text, a.name 
                    FROM poems p 
                    LEFT JOIN authors a ON p.author_id = a.id 
                    ORDER BY RANDOM() 
                    LIMIT 1
                ''')
                
                poem = cursor.fetchone()
                if poem:
                    poem_id, title, text, author_name = poem
                    author_text = f"Автор: {author_name}" if author_name else "Автор: Неизвестен"
                    
                    poem_text = f"📖 **{title}**\n\n{author_text}\n\n{text}"
                    
                    try:
                        await bot.send_message(user_id, poem_text)
                    except Exception as e:
                        logging.error(f"Failed to send notification to {user_id}: {e}")
            
            conn.close()
            
            # Wait based on frequency (simplified - check daily)
            await asyncio.sleep(86400)  # 24 hours
            
        except Exception as e:
            logging.error(f"Error in notification loop: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error

# Main function
async def main():
    # Start notification task
    asyncio.create_task(send_notifications())
    
    # Start the bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())