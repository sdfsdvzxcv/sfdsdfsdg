from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import sqlite3
import os
import PyPDF2
from docx import Document
from werkzeug.utils import secure_filename
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('poetry.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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

def extract_text_from_file(file):
    """Extract text from various file formats"""
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    
    if file_extension == 'txt':
        return file.read().decode('utf-8')
    
    elif file_extension == 'pdf':
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif file_extension in ['doc', 'docx']:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def add_sample_data():
    """Add sample data if database is empty"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we have any data
    cursor.execute('SELECT COUNT(*) FROM poems')
    poem_count = cursor.fetchone()[0]
    
    if poem_count == 0:
        # Add sample authors
        sample_authors = [
            ('Александр Пушкин', 'Россия', 'Золотой век'),
            ('Михаил Лермонтов', 'Россия', 'Золотой век'),
            ('Анна Ахматова', 'Россия', 'Серебряный век'),
            ('Сергей Есенин', 'Россия', 'Серебряный век'),
            ('Марина Цветаева', 'Россия', 'Серебряный век')
        ]
        
        for name, country, period in sample_authors:
            cursor.execute('INSERT INTO authors (name, country, period) VALUES (?, ?, ?)',
                         (name, country, period))
        
        # Get author IDs
        cursor.execute('SELECT id FROM authors')
        author_ids = [row[0] for row in cursor.fetchall()]
        
        # Add sample poems
        sample_poems = [
            ('Я помню чудное мгновенье', 'Я помню чудное мгновенье:\nПередо мной явилась ты,\nКак мимолетное виденье,\nКак гений чистой красоты.', author_ids[0], 'лирика'),
            ('У лукоморья дуб зеленый', 'У лукоморья дуб зеленый;\nЗлатая цепь на дубе том:\nИ днем и ночью кот ученый\nВсе ходит по цепи кругом.', author_ids[0], 'эпика'),
            ('Бородино', '— Скажи-ка, дядя, ведь не даром\nМосква, спаленная пожаром,\nФранцузу отдана?\nВедь были ж схватки боевые,\nДа, говорят, еще какие!\nНедаром помнит вся Россия\nПро день Бородина!', author_ids[1], 'эпика'),
            ('Реквием', 'Нет, и не под чуждым небосводом,\nИ не под защитой чуждых крыл, —\nЯ была тогда с моим народом,\nТам, где мой народ, к несчастью, был.', author_ids[2], 'лирика'),
            ('Не жалею, не зову, не плачу', 'Не жалею, не зову, не плачу,\nВсе пройдет, как с белых яблонь дым.\nУвяданья золотом охваченный,\nЯ не буду больше молодым.', author_ids[3], 'лирика')
        ]
        
        for title, text, author_id, genre in sample_poems:
            cursor.execute('INSERT INTO poems (title, text, author_id, genre) VALUES (?, ?, ?, ?)',
                         (title, text, author_id, genre))
        
        conn.commit()
    
    conn.close()

# Add sample data on first run
add_sample_data()

# Routes
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
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
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
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/poems/random')
def get_random_poem():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
        FROM poems p
        LEFT JOIN authors a ON p.author_id = a.id
        ORDER BY RANDOM()
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    else:
        return jsonify({'error': 'No poems found'}), 404

@app.route('/api/poems/<int:poem_id>')
def get_poem(poem_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
        FROM poems p
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE p.id = ?
    ''', (poem_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    else:
        return jsonify({'error': 'Poem not found'}), 404

@app.route('/api/authors')
def get_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, country, period FROM authors ORDER BY name')
    
    authors = []
    for row in cursor.fetchall():
        authors.append({
            'id': row['id'],
            'name': row['name'],
            'country': row['country'],
            'period': row['period']
        })
    
    conn.close()
    return jsonify(authors)

@app.route('/api/authors/<int:author_id>/poems')
def get_author_poems(author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
        FROM poems p
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE p.author_id = ?
        ORDER BY p.title
    ''', (author_id,))
    
    poems = []
    for row in cursor.fetchall():
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/stats')
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM poems')
    poems = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM authors')
    authors = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM user_submissions WHERE status = "pending"')
    pending_submissions = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'users': users,
        'poems': poems,
        'authors': authors,
        'pending_submissions': pending_submissions
    })

@app.route('/api/library/save', methods=['POST'])
def save_to_library():
    data = request.get_json()
    user_id = data.get('user_id')
    poem_id = data.get('poem_id')
    
    if not user_id or not poem_id:
        return jsonify({'error': 'Missing user_id or poem_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already saved
    cursor.execute('SELECT id FROM user_library WHERE user_id = ? AND poem_id = ?', (user_id, poem_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({'message': 'Already in library'}), 200
    
    cursor.execute('INSERT INTO user_library (user_id, poem_id) VALUES (?, ?)', (user_id, poem_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Saved to library'}), 201

@app.route('/api/library/<int:user_id>')
def get_user_library(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
        FROM user_library ul
        JOIN poems p ON ul.poem_id = p.id
        LEFT JOIN authors a ON p.author_id = a.id
        WHERE ul.user_id = ?
        ORDER BY ul.saved_at DESC
    ''', (user_id,))
    
    poems = []
    for row in cursor.fetchall():
        poems.append({
            'id': row['id'],
            'title': row['title'],
            'text': row['text'],
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    
    conn.close()
    return jsonify(poems)

# Admin API Routes
@app.route('/api/admin/poems')
def admin_get_poems():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.title, p.text, p.genre, a.name as author_name, a.id as author_id
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
            'genre': row['genre'],
            'author_name': row['author_name'],
            'author_id': row['author_id']
        })
    
    conn.close()
    return jsonify(poems)

@app.route('/api/admin/poems', methods=['POST'])
def admin_add_poem():
    data = request.get_json()
    
    title = data.get('title')
    text = data.get('text')
    author_id = data.get('author_id')
    genre = data.get('genre')
    
    if not title or not text:
        return jsonify({'error': 'Missing title or text'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO poems (title, text, author_id, genre) VALUES (?, ?, ?, ?)',
                   (title, text, author_id, genre))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem added successfully'}), 201

@app.route('/api/admin/poems/<int:poem_id>', methods=['DELETE'])
def admin_delete_poem(poem_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM poems WHERE id = ?', (poem_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Poem deleted successfully'}), 200

@app.route('/api/admin/authors')
def admin_get_authors():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, country, period FROM authors ORDER BY name')
    
    authors = []
    for row in cursor.fetchall():
        authors.append({
            'id': row['id'],
            'name': row['name'],
            'country': row['country'],
            'period': row['period']
        })
    
    conn.close()
    return jsonify(authors)

@app.route('/api/admin/authors', methods=['POST'])
def admin_add_author():
    data = request.get_json()
    
    name = data.get('name')
    country = data.get('country')
    period = data.get('period')
    
    if not name:
        return jsonify({'error': 'Missing name'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO authors (name, country, period) VALUES (?, ?, ?)',
                   (name, country, period))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Author added successfully'}), 201

@app.route('/api/admin/authors/<int:author_id>', methods=['DELETE'])
def admin_delete_author(author_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM authors WHERE id = ?', (author_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Author deleted successfully'}), 200

@app.route('/api/admin/submissions')
def admin_get_submissions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT us.id, us.text, u.first_name, u.username, us.created_at, us.status
        FROM user_submissions us
        JOIN users u ON us.user_id = u.id
        WHERE us.status = 'pending'
        ORDER BY us.created_at DESC
    ''')
    
    submissions = []
    for row in cursor.fetchall():
        submissions.append({
            'id': row['id'],
            'text': row['text'],
            'user_name': row['first_name'],
            'username': row['username'],
            'created_at': row['created_at'],
            'status': row['status']
        })
    
    conn.close()
    return jsonify(submissions)

@app.route('/api/admin/submissions/<int:submission_id>/approve', methods=['POST'])
def admin_approve_submission(submission_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE user_submissions SET status = "approved" WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Submission approved'}), 200

@app.route('/api/admin/submissions/<int:submission_id>/reject', methods=['POST'])
def admin_reject_submission(submission_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE user_submissions SET status = "rejected" WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Submission rejected'}), 200

@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    # This is a placeholder for the actual broadcast functionality
    # In a real implementation, this would integrate with the Telegram bot
    data = request.form
    broadcast_type = data.get('type', 'text')
    text = data.get('text', '')
    
    # For now, just return success
    return jsonify({'message': f'Broadcast sent: {broadcast_type}'}), 200

@app.route('/api/admin/upload-poem', methods=['POST'])
def admin_upload_poem():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Extract text from file
            text = extract_text_from_file(file)
            
            # Get other form data
            title = request.form.get('title', 'Uploaded Poem')
            author_id = request.form.get('author_id')
            genre = request.form.get('genre', 'лирика')
            
            # Save to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('INSERT INTO poems (title, text, author_id, genre) VALUES (?, ?, ?, ?)',
                          (title, text, author_id, genre))
            conn.commit()
            conn.close()
            
            return jsonify({'message': 'Poem uploaded successfully'}), 201
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)