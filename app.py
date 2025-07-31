from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import PyPDF2
from docx import Document
from werkzeug.utils import secure_filename
import requests
import json

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('poetry.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
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

def extract_text_from_file(file_path):
    """Extract text from various file formats"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        
        elif file_extension == '.pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        
        elif file_extension in ['.doc', '.docx']:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        else:
            return None
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return None

def add_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM poems')
    poem_count = cursor.fetchone()[0]
    
    if poem_count == 0:
        # Add sample authors
        authors_data = [
            ('Александр Пушкин', 'Россия', 'Романтизм'),
            ('Михаил Лермонтов', 'Россия', 'Романтизм'),
            ('Анна Ахматова', 'Россия', 'Серебряный век'),
            ('Сергей Есенин', 'Россия', 'Серебряный век'),
            ('Марина Цветаева', 'Россия', 'Серебряный век'),
            ('Уильям Шекспир', 'Великобритания', 'Ренессанс'),
            ('Роберт Фрост', 'США', 'Современность'),
            ('Эмили Дикинсон', 'США', 'Романтизм')
        ]
        
        for author in authors_data:
            cursor.execute('''
                INSERT INTO authors (name, country, period)
                VALUES (?, ?, ?)
            ''', author)
        
        # Add sample poems
        poems_data = [
            ('Я помню чудное мгновенье', 1, 'лирика', 'Я помню чудное мгновенье:\nПередо мной явилась ты,\nКак мимолетное виденье,\nКак гений чистой красоты.'),
            ('У лукоморья дуб зеленый', 1, 'эпика', 'У лукоморья дуб зеленый;\nЗлатая цепь на дубе том:\nИ днем и ночью кот ученый\nВсе ходит по цепи кругом.'),
            ('Бородино', 2, 'эпика', '— Скажи-ка, дядя, ведь не даром\nМосква, спаленная пожаром,\nФранцузу отдана?'),
            ('Реквием', 3, 'лирика', 'Нет, и не под чуждым небосводом,\nИ не под защитой чуждых крыл, —\nЯ была тогда с моим народом,\nТам, где мой народ, к несчастью, был.'),
            ('Береза', 4, 'лирика', 'Белая береза\nПод моим окном\nПринакрылась снегом,\nТочно серебром.'),
            ('Мне нравится, что вы больны не мной', 5, 'лирика', 'Мне нравится, что вы больны не мной,\nМне нравится, что я больна не вами,\nЧто никогда тяжелый шар земной\nНе уплывет под нашими ногами.'),
            ('To be or not to be', 6, 'драма', 'To be, or not to be, that is the question:\nWhether tis nobler in the mind to suffer\nThe slings and arrows of outrageous fortune,\nOr to take arms against a sea of troubles.'),
            ('The Road Not Taken', 7, 'лирика', 'Two roads diverged in a yellow wood,\nAnd sorry I could not travel both\nAnd be one traveler, long I stood\nAnd looked down one as far as I could.'),
            ('Hope is the thing with feathers', 8, 'лирика', 'Hope is the thing with feathers\nThat perches in the soul,\nAnd sings the tune without the words,\nAnd never stops at all.')
        ]
        
        for poem in poems_data:
            cursor.execute('''
                INSERT INTO poems (title, author_id, genre, text)
                VALUES (?, ?, ?, ?)
            ''', poem)
        
        # Add sample users
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, first_name, last_name)
            VALUES (1, 'demo_user', 'Демо', 'Пользователь')
        ''')
        
        # Add sample library entries
        cursor.execute('''
            INSERT OR IGNORE INTO user_library (user_id, poem_id)
            VALUES (1, 1), (1, 3), (1, 5)
        ''')
        
        # Add sample submissions
        submissions_data = [
            (1, 'Новое стихотворение', 'Новый автор', 'лирика', 'Это тестовое стихотворение для проверки функционала.'),
            (1, 'Еще одно стихотворение', 'Другой автор', 'эпика', 'Второе тестовое стихотворение.')
        ]
        
        for submission in submissions_data:
            cursor.execute('''
                INSERT INTO user_submissions (user_id, title, author_name, genre, text)
                VALUES (?, ?, ?, ?, ?)
            ''', submission)
        
        conn.commit()
    
    conn.close()

# Initialize database
init_db()
add_sample_data()

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('web', filename)

# API Routes
@app.route('/api/poems')
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
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/poems/random')
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
    if row:
        poem = {
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        }
    else:
        poem = None
    
    conn.close()
    return jsonify(poem)

@app.route('/api/poems/<int:poem_id>')
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
    if row:
        poem = {
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        }
    else:
        poem = None
    
    conn.close()
    return jsonify(poem)

@app.route('/api/authors')
def get_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.*, COUNT(p.id) as poem_count
        FROM authors a
        LEFT JOIN poems p ON a.id = p.author_id
        GROUP BY a.id
        ORDER BY a.name
    ''')
    
    authors = []
    for row in cursor.fetchall():
        authors.append({
            'id': row['id'],
            'name': row['name'],
            'country': row['country'],
            'period': row['period'],
            'poem_count': row['poem_count'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(authors)

@app.route('/api/authors/<int:author_id>/poems')
def get_author_poems(author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, a.name as author_name 
        FROM poems p 
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE p.author_id = ?
        ORDER BY p.created_at DESC
    ''', (author_id,))
    
    poems = []
    for row in cursor.fetchall():
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/library/<int:user_id>')
def get_user_library(user_id):
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
    
    poems = []
    for row in cursor.fetchall():
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/library/<int:user_id>', methods=['POST'])
def save_to_library(user_id):
    data = request.get_json()
    poem_id = data.get('poem_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already in library
    cursor.execute('''
        SELECT id FROM user_library 
        WHERE user_id = ? AND poem_id = ?
    ''', (user_id, poem_id))
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'message': 'Already in library'}), 200
    
    cursor.execute('''
        INSERT INTO user_library (user_id, poem_id)
        VALUES (?, ?)
    ''', (user_id, poem_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Saved to library'}), 201

# Admin API Routes
@app.route('/api/admin/stats')
def admin_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM poems')
    total_poems = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM authors')
    total_authors = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_poems': total_poems,
        'total_authors': total_authors,
        'pending_submissions': pending_submissions
    })

@app.route('/api/admin/poems')
def admin_poems():
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
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/admin/authors')
def admin_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.*, COUNT(p.id) as poem_count
        FROM authors a
        LEFT JOIN poems p ON a.id = p.author_id
        GROUP BY a.id
        ORDER BY a.name
    ''')
    
    authors = []
    for row in cursor.fetchall():
        authors.append({
            'id': row['id'],
            'name': row['name'],
            'country': row['country'],
            'period': row['period'],
            'poem_count': row['poem_count'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(authors)

@app.route('/api/admin/submissions')
def admin_submissions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM user_submissions 
        WHERE status = 'pending'
        ORDER BY created_at DESC
    ''')
    
    submissions = []
    for row in cursor.fetchall():
        submissions.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'title': row['title'],
            'author_name': row['author_name'],
            'genre': row['genre'],
            'text': row['text'],
            'status': row['status'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(submissions)

@app.route('/api/admin/authors', methods=['POST'])
def admin_add_author():
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO authors (name, country, period)
        VALUES (?, ?, ?)
    ''', (data['name'], data.get('country'), data.get('period')))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Author added successfully'}), 201

@app.route('/api/admin/poems/<int:poem_id>', methods=['DELETE'])
def admin_delete_poem(poem_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM poems WHERE id = ?', (poem_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem deleted successfully'}), 200

@app.route('/api/admin/authors/<int:author_id>', methods=['DELETE'])
def admin_delete_author(author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM authors WHERE id = ?', (author_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Author deleted successfully'}), 200

@app.route('/api/admin/submissions/<int:submission_id>/approve', methods=['POST'])
def admin_approve_submission(submission_id):
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
    
    conn.close()
    return jsonify({'message': 'Submission approved'}), 200

@app.route('/api/admin/submissions/<int:submission_id>/reject', methods=['POST'])
def admin_reject_submission(submission_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE user_submissions 
        SET status = 'rejected' 
        WHERE id = ?
    ''', (submission_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Submission rejected'}), 200

@app.route('/api/admin/upload-poem', methods=['POST'])
def admin_upload_poem():
    title = request.form.get('title')
    author_id = request.form.get('author_id')
    genre = request.form.get('genre')
    text = request.form.get('text')
    
    # Handle file upload if provided
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from file
            extracted_text = extract_text_from_file(filepath)
            if extracted_text:
                text = extracted_text
            
            # Clean up file
            os.remove(filepath)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO poems (title, text, author_id, genre)
        VALUES (?, ?, ?, ?)
    ''', (title, text, author_id, genre))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem uploaded successfully'}), 201

@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    broadcast_type = request.form.get('type', 'text')
    text = request.form.get('text', '')
    
    # Send to Telegram bot
    try:
        bot_token = os.getenv('BOT_TOKEN')
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        
        if bot_token:
            # For demo purposes, we'll just log the broadcast
            print(f"Broadcast sent: Type={broadcast_type}, Text={text}")
            
            # In a real implementation, you would send to all users
            # This would require storing user IDs and sending messages via Telegram API
            
            return jsonify({'message': 'Broadcast sent successfully'}), 200
        else:
            return jsonify({'error': 'Bot token not configured'}), 500
            
    except Exception as e:
        print(f"Error sending broadcast: {e}")
        return jsonify({'error': 'Failed to send broadcast'}), 500

# User submission endpoint
@app.route('/api/submit-poem', methods=['POST'])
def submit_poem():
    title = request.form.get('title')
    author_name = request.form.get('author_name')
    genre = request.form.get('genre')
    text = request.form.get('text')
    
    # Handle file upload if provided
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from file
            extracted_text = extract_text_from_file(filepath)
            if extracted_text:
                text = extracted_text
            
            # Clean up file
            os.remove(filepath)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add submission
    cursor.execute('''
        INSERT INTO user_submissions (user_id, title, author_name, genre, text)
        VALUES (?, ?, ?, ?, ?)
    ''', (1, title, author_name, genre, text))  # Demo user ID = 1
    
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Send notification to Telegram admins
    try:
        bot_token = os.getenv('BOT_TOKEN')
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        
        if bot_token and admin_ids:
            message = f"📨 Новое предложение стихотворения\n\nНазвание: {title}\nАвтор: {author_name}\nЖанр: {genre}\n\nТекст:\n{text[:500]}..."
            
            for admin_id in admin_ids:
                if admin_id.strip():
                    # In a real implementation, you would send via Telegram API
                    print(f"Notification to admin {admin_id}: {message}")
                    
    except Exception as e:
        print(f"Error sending admin notification: {e}")
    
    return jsonify({'message': 'Poem submitted for moderation'}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)