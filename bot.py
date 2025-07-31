import asyncio
import sqlite3
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import aiofiles
from PIL import Image, ImageDraw, ImageFont
import io

# Загружаем переменные окружения
load_dotenv()

# Инициализация бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class PoemStates(StatesGroup):
    waiting_for_poem_text = State()
    waiting_for_author_name = State()
    waiting_for_author_country = State()
    waiting_for_author_period = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notification_frequency TEXT DEFAULT 'none'
        )
    ''')
    
    # Таблица авторов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            period TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица стихов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER,
            genre TEXT,
            preview TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES authors (id)
        )
    ''')
    
    # Таблица личной библиотеки пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poem_id INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
        )
    ''')
    
    # Таблица избранных цитат пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poem_id INTEGER,
            quote_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
        )
    ''')
    
    # Таблица предложений от пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Клавиатуры
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Получить стихотворение", callback_data="get_random_poem")],
        [InlineKeyboardButton(text="🔍 Выбрать стихотворение", callback_data="choose_poem")],
        [InlineKeyboardButton(text="📚 Личная библиотека", callback_data="personal_library")],
        [InlineKeyboardButton(text="➕ Добавить стихотворение", callback_data="add_poem")]
    ])
    return keyboard

def get_poem_actions_keyboard(poem_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить в библиотеку", callback_data=f"save_poem_{poem_id}")],
        [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem_id}")],
        [InlineKeyboardButton(text="🔄 Регулярные уведомления", callback_data="notifications")],
        [InlineKeyboardButton(text="⬅️ Предыдущее", callback_data="prev_poem"),
         InlineKeyboardButton(text="Следующее ➡️", callback_data="next_poem")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_choose_poem_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 По автору", callback_data="by_author")],
        [InlineKeyboardButton(text="🌍 По стране", callback_data="by_country")],
        [InlineKeyboardButton(text="⏰ По периоду", callback_data="by_period")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_notification_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневно", callback_data="notify_daily")],
        [InlineKeyboardButton(text="📅 Раз в 2 дня", callback_data="notify_2days")],
        [InlineKeyboardButton(text="📅 Раз в 4 дня", callback_data="notify_4days")],
        [InlineKeyboardButton(text="📅 Еженедельно", callback_data="notify_weekly")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_poem")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return keyboard

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Регистрируем пользователя
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()
    
    welcome_text = """
🎭 Добро пожаловать в «Рильке» - маленький мостик к большой поэзии!

Пара кликов – и стихотворение уже на вашем экране, новое и случайное или искомое и давно любимое. В метро, в пробке, очереди за кофе – всегда найдётся несколько минут обратиться к прекрасному.

Выберите действие:
    """
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📖 Как пользоваться ботом:

🎯 **Получить стихотворение** - случайное стихотворение из библиотеки
🔍 **Выбрать стихотворение** - поиск по автору, стране или периоду
📚 **Личная библиотека** - ваши сохраненные стихи
➕ **Добавить стихотворение** - предложить новое стихотворение

💡 Выделяйте цитаты в тексте стихов - они сохранятся в вашем профиле!
    """
    await message.answer(help_text, reply_markup=get_main_keyboard())

# Обработчики callback
@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎭 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "get_random_poem")
async def get_random_poem(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.content, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY RANDOM() 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        poem_id, title, content, author = result
        poem_text = f"📖 **{title}**\n\n"
        if author:
            poem_text += f"👤 *{author}*\n\n"
        poem_text += f"{content}"
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=get_poem_actions_keyboard(poem_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📚 Библиотека пока пуста. Добавьте первое стихотворение!",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data == "choose_poem")
async def choose_poem(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔍 Выберите способ поиска стихотворения:",
        reply_markup=get_choose_poem_keyboard()
    )

@dp.callback_query(lambda c: c.data == "by_author")
async def by_author(callback: types.CallbackQuery):
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name FROM authors ORDER BY name')
    authors = cursor.fetchall()
    conn.close()
    
    if authors:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for author_id, author_name in authors:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=author_name, callback_data=f"author_{author_id}")
            ])
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="➕ Добавить автора", callback_data="add_author")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="choose_poem")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            "👤 Выберите автора:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📚 Авторы не найдены. Добавьте первого автора!",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("author_"))
async def show_author_poems(callback: types.CallbackQuery):
    author_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM authors WHERE id = ?', (author_id,))
    author_name = cursor.fetchone()[0]
    
    cursor.execute('SELECT id, title FROM poems WHERE author_id = ? ORDER BY title', (author_id,))
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for poem_id, title in poems:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=title, callback_data=f"poem_{poem_id}")
            ])
        keyboard.inline_keyboard.extend([
            [InlineKeyboardButton(text="➕ Добавить стихотворение", callback_data="add_poem")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="by_author")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"📖 Стихи автора *{author_name}*:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"📚 У автора *{author_name}* пока нет стихов.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("poem_"))
async def show_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.content, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, content, author = result
        poem_text = f"📖 **{title}**\n\n"
        if author:
            poem_text += f"👤 *{author}*\n\n"
        poem_text += f"{content}"
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=get_poem_actions_keyboard(poem_id),
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("save_poem_"))
async def save_poem_to_library(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    poem_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    # Проверяем, не сохранено ли уже
    cursor.execute('SELECT id FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    if cursor.fetchone():
        await callback.answer("💾 Стихотворение уже в вашей библиотеке!")
        return
    
    cursor.execute('INSERT INTO user_library (user_id, poem_id) VALUES (?, ?)', (user_id, poem_id))
    conn.commit()
    conn.close()
    
    await callback.answer("✅ Стихотворение добавлено в библиотеку!")

@dp.callback_query(lambda c: c.data.startswith("share_poem_"))
async def share_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.content, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, content, author = result
        share_text = f"📖 {title}\n\n"
        if author:
            share_text += f"👤 {author}\n\n"
        share_text += f"{content}\n\n"
        share_text += "📱 Поделено через @RilkePoetryBot"
        
        await callback.message.answer(share_text)

@dp.callback_query(lambda c: c.data == "notifications")
async def notifications_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔄 Выберите частоту уведомлений:",
        reply_markup=get_notification_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("notify_"))
async def set_notification_frequency(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    frequency = callback.data.split("_")[1]
    
    frequency_map = {
        "daily": "daily",
        "2days": "2days", 
        "4days": "4days",
        "weekly": "weekly"
    }
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET notification_frequency = ? WHERE user_id = ?', 
                  (frequency_map.get(frequency, "none"), user_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "✅ Ваш выбор сохранён!",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "personal_library")
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
        ORDER BY ul.added_at DESC
    ''', (user_id,))
    
    poems = cursor.fetchall()
    conn.close()
    
    if poems:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for poem_id, title, author in poems:
            display_text = f"{title}"
            if author:
                display_text += f" - {author}"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=display_text, callback_data=f"lib_poem_{poem_id}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "📚 Ваша личная библиотека:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📚 Ваша библиотека пуста. Сохраните первое стихотворение!",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("lib_poem_"))
async def show_library_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.title, p.content, a.name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        title, content, author = result
        poem_text = f"📖 **{title}**\n\n"
        if author:
            poem_text += f"👤 *{author}*\n\n"
        poem_text += f"{content}"
        
        # Клавиатура для библиотеки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_poem_{poem_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить из библиотеки", callback_data=f"remove_from_lib_{poem_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="personal_library")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            poem_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith("remove_from_lib_"))
async def remove_from_library(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    poem_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    conn.commit()
    conn.close()
    
    await callback.answer("🗑️ Стихотворение удалено из библиотеки!")
    await personal_library(callback)

@dp.callback_query(lambda c: c.data == "add_poem")
async def add_poem_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "➕ Добавление стихотворения\n\n"
        "Напишите текст стихотворения и отправьте его.\n"
        "Ваше предложение будет рассмотрено модератором.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )
    
    # Устанавливаем состояние ожидания текста стихотворения
    from aiogram.fsm.context import FSMContext
    state = FSMContext(storage=storage, key=types.Chat.get_current().id)
    await state.set_state(PoemStates.waiting_for_poem_text)

# Обработчик текста для добавления стихотворения
@dp.message(PoemStates.waiting_for_poem_text)
async def process_poem_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    content = message.text
    
    conn = sqlite3.connect('poetry.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_submissions (user_id, content) 
        VALUES (?, ?)
    ''', (user_id, content))
    conn.commit()
    conn.close()
    
    await message.answer(
        "✅ Ваше стихотворение отправлено модератору на рассмотрение!\n"
        "Мы уведомим вас, когда оно будет добавлено в библиотеку.",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()

# Функция для отправки уведомлений
async def send_notifications():
    while True:
        conn = sqlite3.connect('poetry.db')
        cursor = conn.cursor()
        
        # Получаем пользователей с активными уведомлениями
        cursor.execute('SELECT user_id, notification_frequency FROM users WHERE notification_frequency != "none"')
        users = cursor.fetchall()
        
        for user_id, frequency in users:
            # Проверяем, нужно ли отправлять уведомление
            cursor.execute('SELECT last_notification FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                last_notification = datetime.fromisoformat(result[0])
                now = datetime.now()
                
                # Проверяем интервал
                should_send = False
                if frequency == "daily" and (now - last_notification).days >= 1:
                    should_send = True
                elif frequency == "2days" and (now - last_notification).days >= 2:
                    should_send = True
                elif frequency == "4days" and (now - last_notification).days >= 4:
                    should_send = True
                elif frequency == "weekly" and (now - last_notification).days >= 7:
                    should_send = True
                
                if should_send:
                    # Отправляем случайное стихотворение
                    cursor.execute('''
                        SELECT p.title, p.content, a.name 
                        FROM poems p 
                        LEFT JOIN authors a ON p.author_id = a.id 
                        ORDER BY RANDOM() 
                        LIMIT 1
                    ''')
                    
                    result = cursor.fetchone()
                    if result:
                        title, content, author = result
                        poem_text = f"📖 **{title}**\n\n"
                        if author:
                            poem_text += f"👤 *{author}*\n\n"
                        poem_text += f"{content}"
                        
                        try:
                            await bot.send_message(user_id, poem_text, parse_mode="Markdown")
                            cursor.execute('UPDATE users SET last_notification = ? WHERE user_id = ?', 
                                        (now.isoformat(), user_id))
                        except Exception as e:
                            print(f"Error sending notification to {user_id}: {e}")
        
        conn.commit()
        conn.close()
        
        # Проверяем каждые 6 часов
        await asyncio.sleep(6 * 60 * 60)

# Запуск бота
async def main():
    # Инициализируем базу данных
    init_db()
    
    # Запускаем задачу уведомлений
    asyncio.create_task(send_notifications())
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())