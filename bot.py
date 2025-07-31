import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aioschedule

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM States
class PoemStates(StatesGroup):
    waiting_for_poem_text = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_media = State()

def get_db_connection():
    conn = sqlite3.connect('poetry.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            period TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poem_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            author_name TEXT NOT NULL,
            genre TEXT,
            text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            frequency TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Получить стихотворение", callback_data="get_poem")],
        [InlineKeyboardButton(text="🔍 Выбрать стихотворение", callback_data="choose_poem")],
        [InlineKeyboardButton(text="📚 Личная библиотека", callback_data="library")],
        [InlineKeyboardButton(text="➕ Добавить стихотворение или автора", callback_data="add_poem")]
    ])
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Управление стихотворениями", callback_data="admin_poems")],
        [InlineKeyboardButton(text="👤 Управление авторами", callback_data="admin_authors")],
        [InlineKeyboardButton(text="📨 Модерация предложений", callback_data="admin_submissions")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ])
    return keyboard

def get_poem_actions_keyboard(poem_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить в библиотеку", callback_data=f"save_poem_{poem_id}")],
        [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem_id}")],
        [InlineKeyboardButton(text="🔔 Настроить уведомления", callback_data="set_notification")],
        [InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_poem"),
         InlineKeyboardButton(text="Следующее ➡️", callback_data="next_poem")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_notification_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневно", callback_data="notify_daily")],
        [InlineKeyboardButton(text="📅 Каждые 2 дня", callback_data="notify_2days")],
        [InlineKeyboardButton(text="📅 Каждые 4 дня", callback_data="notify_4days")],
        [InlineKeyboardButton(text="📅 Еженедельно", callback_data="notify_weekly")],
        [InlineKeyboardButton(text="❌ Отключить уведомления", callback_data="notify_off")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_choose_poem_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 По автору", callback_data="search_by_author")],
        [InlineKeyboardButton(text="🌍 По стране", callback_data="search_by_country")],
        [InlineKeyboardButton(text="⏰ По периоду", callback_data="search_by_period")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_library_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Показать все сохраненные", callback_data="show_all_saved")],
        [InlineKeyboardButton(text="🔍 Найти по автору", callback_data="find_by_author")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

# Command handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Register user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()
    
    welcome_text = f"""
🎭 Добро пожаловать в Рильке!

Маленький мостик к большой поэзии.

Здесь вы можете:
• Получить случайное стихотворение
• Найти стихотворение по автору, стране или периоду
• Сохранить понравившиеся стихи в личную библиотеку
• Получать регулярные уведомления
• Предложить новое стихотворение

Выберите действие:
"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in ADMIN_IDS:
        await message.answer("🔧 Панель администратора", reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ У вас нет доступа к админ-панели.")

# Callback query handlers
@dp.callback_query(lambda c: c.data == "get_poem")
async def get_random_poem(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id
        ORDER BY RANDOM() 
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        poem_text = f"""
📖 {row['title']}

👤 Автор: {row['author_name']}
📝 Жанр: {row['genre'] or 'Не указан'}

{row['text']}
        """
        
        await callback.message.edit_text(poem_text, reply_markup=get_poem_actions_keyboard(row['id']))
    else:
        await callback.message.edit_text("❌ Стихотворения не найдены.", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "choose_poem")
async def choose_poem(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔍 Выберите способ поиска стихотворения:",
        reply_markup=get_choose_poem_keyboard()
    )

@dp.callback_query(lambda c: c.data == "search_by_author")
async def search_by_author(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT name FROM authors ORDER BY name')
    authors = cursor.fetchall()
    conn.close()
    
    if authors:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for author in authors:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=author['name'], callback_data=f"author_{author['name']}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "👤 Выберите автора:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "❌ Авторы не найдены.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("author_"))
async def author_selected(callback: types.CallbackQuery):
    author_name = callback.data.replace("author_", "")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE a.name = ?
        ORDER BY p.title
    ''', (author_name,))
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        # Show first poem
        poem = poems[0]
        poem_text = f"""
📖 {poem['title']}

👤 Автор: {poem['author_name']}
📝 Жанр: {poem['genre'] or 'Не указан'}

{poem['text']}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💾 Сохранить в библиотеку", callback_data=f"save_poem_{poem['id']}")],
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem['id']}")],
            [InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_poem"),
             InlineKeyboardButton(text="Следующее ➡️", callback_data="next_poem")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(poem_text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            f"❌ Стихотворения автора {author_name} не найдены.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data == "library")
async def library_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📚 Личная библиотека\n\nЗдесь хранятся ваши сохраненные стихотворения.",
        reply_markup=get_library_keyboard()
    )

@dp.callback_query(lambda c: c.data == "show_all_saved")
async def show_all_saved(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM user_library ul
        JOIN poems p ON ul.poem_id = p.id
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE ul.user_id = ?
        ORDER BY ul.created_at DESC
    ''', (user_id,))
    
    saved_poems = cursor.fetchall()
    conn.close()
    
    if saved_poems:
        poem = saved_poems[0]
        poem_text = f"""
📖 {poem['title']}

👤 Автор: {poem['author_name']}
📝 Жанр: {poem['genre'] or 'Не указан'}

{poem['text']}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить из библиотеки", callback_data=f"remove_from_library_{poem['id']}")],
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem['id']}")],
            [InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_saved"),
             InlineKeyboardButton(text="Следующее ➡️", callback_data="next_saved")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(poem_text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "📚 Ваша библиотека пуста.\n\nСохраните стихотворения, чтобы они появились здесь.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("save_poem_"))
async def save_poem(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    poem_id = int(callback.data.replace("save_poem_", ""))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already saved
    cursor.execute('''
        SELECT id FROM user_library 
        WHERE user_id = ? AND poem_id = ?
    ''', (user_id, poem_id))
    
    if cursor.fetchone():
        await callback.answer("💾 Стихотворение уже в библиотеке!")
    else:
        cursor.execute('''
            INSERT INTO user_library (user_id, poem_id)
            VALUES (?, ?)
        ''', (user_id, poem_id))
        conn.commit()
        await callback.answer("✅ Стихотворение добавлено в библиотеку!")
    
    conn.close()

@dp.callback_query(lambda c: c.data == "set_notification")
async def set_notification(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔔 Настройка уведомлений\n\nВыберите частоту получения случайных стихотворений:",
        reply_markup=get_notification_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("notify_"))
async def set_notification_frequency(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    frequency = callback.data.replace("notify_", "")
    
    if frequency == "off":
        frequency = "none"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update or insert notification setting
    cursor.execute('''
        INSERT OR REPLACE INTO user_notifications (user_id, frequency, is_active)
        VALUES (?, ?, ?)
    ''', (user_id, frequency, 1 if frequency != "none" else 0))
    
    conn.commit()
    conn.close()
    
    if frequency == "none":
        await callback.message.edit_text(
            "🔕 Уведомления отключены.",
            reply_markup=get_main_keyboard()
        )
    else:
        frequency_text = {
            "daily": "ежедневно",
            "2days": "каждые 2 дня",
            "4days": "каждые 4 дня",
            "weekly": "еженедельно"
        }
        await callback.message.edit_text(
            f"🔔 Уведомления настроены: {frequency_text.get(frequency, frequency)}",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data == "add_poem")
async def add_poem_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "➕ Добавить стихотворение\n\n"
        "Отправьте текст стихотворения, которое хотите предложить для добавления в библиотеку.\n\n"
        "Пожалуйста, укажите:\n"
        "• Название стихотворения\n"
        "• Автора\n"
        "• Полный текст\n\n"
        "Ваше предложение будет рассмотрено модератором.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )
    await PoemStates.waiting_for_poem_text.set()

@dp.message(PoemStates.waiting_for_poem_text)
async def add_poem_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_info = f"Пользователь: {message.from_user.first_name} (@{message.from_user.username or 'без username'})"
    
    # Save submission to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_submissions (user_id, title, author_name, genre, text)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, "Предложенное стихотворение", "Неизвестный автор", "лирика", message.text))
    
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Send to admins
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
        "✅ Ваше предложение отправлено на модерацию!\n\n"
        "Мы рассмотрим его и добавим в библиотеку, если оно подходит.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )

# Admin callback handlers
@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM poems')
    total_poems = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM authors')
    total_authors = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 Статистика проекта

👥 Пользователей: {total_users}
📖 Стихотворений: {total_poems}
👤 Авторов: {total_authors}
📨 Ожидают модерации: {pending_submissions}
    """
    
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(lambda c: c.data == "admin_poems")
async def admin_poems(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id
        ORDER BY p.created_at DESC
        LIMIT 10
    ''')
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        text = "📝 Последние стихотворения:\n\n"
        for poem in poems:
            text += f"• {poem['title']} - {poem['author_name']}\n"
        text += "\nДля полного управления используйте веб-панель."
    else:
        text = "❌ Стихотворения не найдены."
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@dp.callback_query(lambda c: c.data == "admin_authors")
async def admin_authors(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM authors ORDER BY name LIMIT 10')
    authors = cursor.fetchall()
    conn.close()
    
    if authors:
        text = "👤 Последние авторы:\n\n"
        for author in authors:
            text += f"• {author['name']} ({author['country'] or 'Не указана'})\n"
        text += "\nДля полного управления используйте веб-панель."
    else:
        text = "❌ Авторы не найдены."
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@dp.callback_query(lambda c: c.data == "admin_submissions")
async def admin_submissions(callback: types.CallbackQuery):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM user_submissions 
        WHERE status = 'pending'
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    
    submissions = cursor.fetchall()
    conn.close()
    
    if submissions:
        text = "📨 Последние предложения:\n\n"
        for submission in submissions:
            text += f"• {submission['title']} - {submission['author_name']}\n"
        text += "\nДля полной модерации используйте веб-панель."
    else:
        text = "✅ Нет предложений для модерации."
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )
    await AdminStates.waiting_for_broadcast_text.set()

@dp.message(AdminStates.waiting_for_broadcast_text)
async def admin_broadcast_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    
    await message.answer(
        f"📢 Текст рассылки:\n\n{message.text}\n\n"
        "Отправьте медиа файл (фото, видео, GIF) или нажмите 'Отправить текст':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить текст", callback_data="send_broadcast_text")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )
    await AdminStates.waiting_for_broadcast_media.set()

@dp.callback_query(lambda c: c.data == "send_broadcast_text")
async def send_broadcast_text(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    
    # Send to all users
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    for user in users:
        try:
            await bot.send_message(user['id'], f"📢 Рассылка:\n\n{text}")
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to user {user['id']}: {e}")
    
    await callback.message.edit_text(
        f"✅ Рассылка отправлена {sent_count} пользователям!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.message(AdminStates.waiting_for_broadcast_media)
async def admin_broadcast_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    
    # Send to all users
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    for user in users:
        try:
            if message.photo:
                await bot.send_photo(user['id'], message.photo[-1].file_id, caption=text)
            elif message.video:
                await bot.send_video(user['id'], message.video.file_id, caption=text)
            elif message.animation:
                await bot.send_animation(user['id'], message.animation.file_id, caption=text)
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to user {user['id']}: {e}")
    
    await message.answer(
        f"✅ Рассылка с медиа отправлена {sent_count} пользователям!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("admin_approve_submission_"))
async def admin_approve_submission(callback: types.CallbackQuery):
    submission_id = int(callback.data.replace("admin_approve_submission_", ""))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get submission data
    cursor.execute('SELECT * FROM user_submissions WHERE id = ?', (submission_id,))
    submission = cursor.fetchone()
    
    if submission:
        # Add author if doesn't exist
        cursor.execute('SELECT id FROM authors WHERE name = ?', (submission['author_name'],))
        author = cursor.fetchone()
        
        if not author:
            cursor.execute('INSERT INTO authors (name) VALUES (?)', (submission['author_name'],))
            author_id = cursor.lastrowid
        else:
            author_id = author['id']
        
        # Add poem
        cursor.execute('''
            INSERT INTO poems (title, text, author_id, genre)
            VALUES (?, ?, ?, ?)
        ''', (submission['title'], submission['text'], author_id, submission['genre']))
        
        # Update submission status
        cursor.execute('''
            UPDATE user_submissions 
            SET status = 'approved' 
            WHERE id = ?
        ''', (submission_id,))
        
        conn.commit()
        
        await callback.message.edit_text(
            f"✅ Предложение одобрено!\n\nСтихотворение '{submission['title']}' добавлено в библиотеку.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Предложение не найдено.",
            reply_markup=get_admin_keyboard()
        )
    
    conn.close()

@dp.callback_query(lambda c: c.data.startswith("admin_reject_submission_"))
async def admin_reject_submission(callback: types.CallbackQuery):
    submission_id = int(callback.data.replace("admin_reject_submission_", ""))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE user_submissions 
        SET status = 'rejected' 
        WHERE id = ?
    ''', (submission_id,))
    
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "❌ Предложение отклонено.",
        reply_markup=get_admin_keyboard()
    )

# Scheduled notifications
async def send_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get users with active notifications
    cursor.execute('''
        SELECT user_id, frequency FROM user_notifications 
        WHERE is_active = 1
    ''')
    
    notifications = cursor.fetchall()
    
    # Get random poem
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id
        ORDER BY RANDOM() 
        LIMIT 1
    ''')
    
    poem = cursor.fetchone()
    conn.close()
    
    if poem:
        poem_text = f"""
📖 Случайное стихотворение дня

{poem['title']}

👤 Автор: {poem['author_name']}
📝 Жанр: {poem['genre'] or 'Не указан'}

{poem['text']}
        """
        
        for notification in notifications:
            try:
                await bot.send_message(notification['user_id'], poem_text)
            except Exception as e:
                logging.error(f"Failed to send notification to user {notification['user_id']}: {e}")

async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

async def main():
    # Initialize database
    init_db()
    
    # Setup scheduled tasks
    aioschedule.every().day.at("09:00").do(send_notifications)
    aioschedule.every(2).days.at("09:00").do(send_notifications)
    aioschedule.every(4).days.at("09:00").do(send_notifications)
    aioschedule.every().week.at("09:00").do(send_notifications)
    
    # Start scheduler
    asyncio.create_task(scheduler())
    
    # Start bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())