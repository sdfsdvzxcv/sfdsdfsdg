from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import re

app = Flask(__name__)
CORS(app)

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('poetry.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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

# Инициализация базы данных
init_db()

# Статические файлы
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('web', filename)

# API endpoints

@app.route('/api/poems', methods=['GET'])
def get_poems():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY p.created_at DESC
    ''')
    
    poems = []
    for row in cursor.fetchall():
        poem = dict(row)
        poems.append(poem)
    
    conn.close()
    return jsonify({'poems': poems})

@app.route('/api/poems/random', methods=['GET'])
def get_random_poem():
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
        return jsonify({'poem': dict(row)})
    else:
        return jsonify({'error': 'No poems found'}), 404

@app.route('/api/poems/<int:poem_id>', methods=['GET'])
def get_poem(poem_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.id = ?
    ''', (poem_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({'poem': dict(row)})
    else:
        return jsonify({'error': 'Poem not found'}), 404

@app.route('/api/authors', methods=['GET'])
def get_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM authors ORDER BY name')
    
    authors = []
    for row in cursor.fetchall():
        authors.append(dict(row))
    
    conn.close()
    return jsonify({'authors': authors})

@app.route('/api/authors/<int:author_id>/poems', methods=['GET'])
def get_author_poems(author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        WHERE p.author_id = ?
        ORDER BY p.title
    ''', (author_id,))
    
    poems = []
    for row in cursor.fetchall():
        poems.append(dict(row))
    
    conn.close()
    return jsonify({'poems': poems})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Статистика пользователей
    cursor.execute('SELECT COUNT(*) as count FROM users')
    total_users = cursor.fetchone()['count']
    
    # Статистика стихов
    cursor.execute('SELECT COUNT(*) as count FROM poems')
    total_poems = cursor.fetchone()['count']
    
    # Статистика авторов
    cursor.execute('SELECT COUNT(*) as count FROM authors')
    total_authors = cursor.fetchone()['count']
    
    # Статистика предложений
    cursor.execute('SELECT COUNT(*) as count FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_poems': total_poems,
        'total_authors': total_authors,
        'pending_submissions': pending_submissions
    })

@app.route('/api/library/save', methods=['POST'])
def save_poem_to_library():
    data = request.get_json()
    poem_id = data.get('poem_id')
    user_id = data.get('user_id', 1)  # Временное решение
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, не сохранено ли уже
    cursor.execute('SELECT id FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Poem already in library'}), 400
    
    cursor.execute('INSERT INTO user_library (user_id, poem_id) VALUES (?, ?)', (user_id, poem_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem saved to library'})

@app.route('/api/library/<int:user_id>', methods=['GET'])
def get_user_library(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name, ul.added_at
        FROM user_library ul
        JOIN poems p ON ul.poem_id = p.id
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE ul.user_id = ?
        ORDER BY ul.added_at DESC
    ''', (user_id,))
    
    poems = []
    for row in cursor.fetchall():
        poems.append(dict(row))
    
    conn.close()
    return jsonify({'poems': poems})

# Админ endpoints

@app.route('/api/admin/poems', methods=['GET'])
def admin_get_poems():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id 
        ORDER BY p.created_at DESC
    ''')
    
    poems = []
    for row in cursor.fetchall():
        poems.append(dict(row))
    
    conn.close()
    return jsonify({'poems': poems})

@app.route('/api/admin/poems', methods=['POST'])
def admin_add_poem():
    data = request.get_json()
    
    title = data.get('title')
    content = data.get('content')
    author_id = data.get('author_id')
    genre = data.get('genre')
    preview = data.get('preview')
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO poems (title, content, author_id, genre, preview)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, content, author_id, genre, preview))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem added successfully'})

@app.route('/api/admin/authors', methods=['GET'])
def admin_get_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.*, COUNT(p.id) as poems_count
        FROM authors a
        LEFT JOIN poems p ON a.id = p.author_id
        GROUP BY a.id
        ORDER BY a.name
    ''')
    
    authors = []
    for row in cursor.fetchall():
        authors.append(dict(row))
    
    conn.close()
    return jsonify({'authors': authors})

@app.route('/api/admin/authors', methods=['POST'])
def admin_add_author():
    data = request.get_json()
    
    name = data.get('name')
    country = data.get('country')
    period = data.get('period')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO authors (name, country, period)
        VALUES (?, ?, ?)
    ''', (name, country, period))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Author added successfully'})

@app.route('/api/admin/submissions', methods=['GET'])
def admin_get_submissions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.*, u.username, u.first_name, u.last_name
        FROM user_submissions us
        LEFT JOIN users u ON us.user_id = u.user_id
        WHERE us.status = 'pending'
        ORDER BY us.created_at DESC
    ''')
    
    submissions = []
    for row in cursor.fetchall():
        submission = dict(row)
        submission['user_name'] = submission.get('username') or submission.get('first_name') or 'Пользователь'
        submissions.append(submission)
    
    conn.close()
    return jsonify({'submissions': submissions})

@app.route('/api/admin/submissions/<int:submission_id>/approve', methods=['POST'])
def admin_approve_submission(submission_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем данные предложения
    cursor.execute('SELECT user_id, content FROM user_submissions WHERE id = ?', (submission_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Submission not found'}), 404
    
    user_id, content = row['user_id'], row['content']
    
    # Обновляем статус предложения
    cursor.execute('UPDATE user_submissions SET status = "approved" WHERE id = ?', (submission_id,))
    
    # Добавляем стихотворение
    cursor.execute('''
        INSERT INTO poems (title, content, author_id)
        VALUES (?, ?, NULL)
    ''', ("Предложенное стихотворение", content))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Submission approved'})

@app.route('/api/admin/submissions/<int:submission_id>/reject', methods=['POST'])
def admin_reject_submission(submission_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE user_submissions SET status = "rejected" WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Submission rejected'})

@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    data = request.form
    broadcast_type = data.get('type', 'text')
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    # Здесь должна быть логика отправки сообщений всем пользователям
    # Пока просто возвращаем успех
    return jsonify({'message': 'Broadcast sent successfully'})

@app.route('/api/admin/upload-poem', methods=['POST'])
def admin_upload_poem():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Извлекаем текст из файла
        content = extract_text_from_file(filepath)
        
        # Удаляем временный файл
        os.remove(filepath)
        
        if content:
            # Добавляем в базу данных
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Пытаемся извлечь название из первой строки
            lines = content.split('\n')
            title = lines[0].strip() if lines else "Загруженное стихотворение"
            
            cursor.execute('''
                INSERT INTO poems (title, content)
                VALUES (?, ?)
            ''', (title, content))
            
            conn.commit()
            conn.close()
            
            return jsonify({'message': 'File processed successfully'})
        else:
            return jsonify({'error': 'Could not extract text from file'}), 400
    
    return jsonify({'error': 'Invalid file type'}), 400

def extract_text_from_file(filepath):
    """Извлекает текст из различных типов файлов"""
    try:
        ext = filepath.rsplit('.', 1)[1].lower()
        
        if ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == 'pdf':
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        
        elif ext in ['doc', 'docx']:
            doc = docx.Document(filepath)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        else:
            return None
    
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

# Добавление тестовых данных
def add_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже данные
    cursor.execute('SELECT COUNT(*) FROM poems')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Добавляем авторов
    authors_data = [
        ('Александр Пушкин', 'Россия', 'Золотой век'),
        ('Михаил Лермонтов', 'Россия', 'Золотой век'),
        ('Анна Ахматова', 'Россия', 'Серебряный век'),
        ('Сергей Есенин', 'Россия', 'Серебряный век'),
        ('Марина Цветаева', 'Россия', 'Серебряный век')
    ]
    
    for name, country, period in authors_data:
        cursor.execute('INSERT INTO authors (name, country, period) VALUES (?, ?, ?)', (name, country, period))
    
    # Получаем ID авторов
    cursor.execute('SELECT id FROM authors')
    author_ids = [row[0] for row in cursor.fetchall()]
    
    # Добавляем стихотворения
    poems_data = [
        ('Я помню чудное мгновенье', 'Я помню чудное мгновенье:\nПередо мной явилась ты,\nКак мимолетное виденье,\nКак гений чистой красоты.', author_ids[0], 'Лирика'),
        ('У лукоморья дуб зеленый', 'У лукоморья дуб зеленый;\nЗлатая цепь на дубе том:\nИ днем и ночью кот ученый\nВсе ходит по цепи кругом.', author_ids[0], 'Сказка'),
        ('Бородино', '— Скажи-ка, дядя, ведь не даром\nМосква, спаленная пожаром,\nФранцузу отдана?', author_ids[1], 'Патриотическая лирика'),
        ('Родина', 'Люблю отчизну я, но странною любовью!\nНе победит ее рассудок мой.', author_ids[1], 'Патриотическая лирика'),
        ('Муза', 'Когда я ночью жду ее прихода,\nЖизнь, кажется, висит на волоске.', author_ids[2], 'Лирика'),
        ('Береза', 'Белая береза\nПод моим окном\nПринакрылась снегом,\nТочно серебром.', author_ids[3], 'Пейзажная лирика'),
        ('Письмо к женщине', 'Вы помните,\nВы все, конечно, помните,\nКак я стоял,\nПриблизившись к стене.', author_ids[3], 'Лирика'),
        ('Молитва', 'В час, когда над миром\nБог склоняет лик,\nИ звезда с звездою\nГоворит навек.', author_ids[4], 'Философская лирика')
    ]
    
    for title, content, author_id, genre in poems_data:
        preview = content.split('\n')[0] + '...'
        cursor.execute('''
            INSERT INTO poems (title, content, author_id, genre, preview)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, author_id, genre, preview))
    
    conn.commit()
    conn.close()
    print("Sample data added successfully!")

if __name__ == '__main__':
    # Добавляем тестовые данные при первом запуске
    add_sample_data()
    
    app.run(debug=True, host='0.0.0.0', port=5000)