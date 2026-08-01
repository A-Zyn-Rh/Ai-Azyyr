import os
import sqlite3
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Import fungsi AI kamu dari ai_service.py
from ai_service import generate_ai_response

# Penentuan lokasi DB (khusus Vercel menggunakan /tmp)
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/database.db'
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    DB_PATH = 'database.db'
    UPLOAD_FOLDER = 'static/uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # 1. Tabel Sesi Chat untuk Sidebar
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                chat_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                title TEXT DEFAULT 'Chat Baru',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 2. Tabel Pesan Per Percakapan
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT,
                file_path TEXT,
                file_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

# --- API 1: DAFTAR SESI DI SIDEBAR ---
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({'success': False, 'error': 'device_id required'}), 400

    with get_db() as conn:
        sessions = conn.execute('''
            SELECT chat_id, title, updated_at 
            FROM chat_sessions 
            WHERE device_id = ? 
            ORDER BY updated_at DESC
        ''', (device_id,)).fetchall()

    return jsonify({
        'success': True,
        'sessions': [dict(s) for s in sessions]
    })

# --- API 2: AMBIL RIWAYAT CHAT SPESIFIK ---
@app.route('/api/history', methods=['GET'])
def get_history():
    device_id = request.args.get('device_id')
    chat_id = request.args.get('chat_id')

    if not device_id:
        return jsonify({'success': False, 'error': 'device_id required'}), 400

    with get_db() as conn:
        if chat_id and chat_id not in ['null', 'undefined', '']:
            messages = conn.execute('''
                SELECT sender, content, file_path, file_type, timestamp 
                FROM messages 
                WHERE device_id = ? AND chat_id = ? 
                ORDER BY id ASC
            ''', (device_id, chat_id)).fetchall()
        else:
            messages = []

    return jsonify({
        'success': True,
        'history': [dict(m) for m in messages]
    })

# --- API 3: KIRIM PESAN & PROSES AI ---
@app.route('/api/chat', methods=['POST'])
def handle_chat():
    device_id = request.form.get('device_id')
    chat_id = request.form.get('chat_id')
    message = request.form.get('message', '').strip()

    if not device_id:
        return jsonify({'success': False, 'error': 'device_id required'}), 400

    # Handle Upload File jika ada
    file_path = None
    file_type = None
    file_name = None
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(saved_path)
            file_path = f"/static/uploads/{filename}" if not os.environ.get('VERCEL') else f"/tmp/uploads/{filename}"
            file_name = filename
            
            ext = filename.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                file_type = 'image'
            elif ext in ['mp4', 'webm', 'mov']:
                file_type = 'video'
            else:
                file_type = 'document'

    # Buat Sesi Baru jika belum ada chat_id
    if not chat_id or chat_id in ['null', 'undefined', '']:
        chat_id = f"session-{uuid.uuid4().hex[:10]}"
        
        # Buat Judul Otomatis dari 30 karakter pertama
        title = message[:30] + ("..." if len(message) > 30 else "") if message else f"Berkas: {file_name}"

        with get_db() as conn:
            conn.execute('''
                INSERT INTO chat_sessions (chat_id, device_id, title)
                VALUES (?, ?, ?)
            ''', (chat_id, device_id, title))
            conn.commit()

    # Simpan Pesan User
    with get_db() as conn:
        conn.execute('''
            INSERT INTO messages (chat_id, device_id, sender, content, file_path, file_type)
            VALUES (?, ?, 'user', ?, ?, ?)
        ''', (chat_id, device_id, message, file_path, file_type))
        
        conn.execute('UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?', (chat_id,))
        conn.commit()

    # Ambil Riwayat Percakapan Lama untuk dikirim ke API AI
    with get_db() as conn:
        history_rows = conn.execute('''
            SELECT sender, content FROM messages 
            WHERE chat_id = ? ORDER BY id ASC
        ''', (chat_id,)).fetchall()

    history_for_ai = []
    for row in history_rows:
        role = "user" if row['sender'] == 'user' else "assistant"
        if row['content']:
            history_for_ai.append({"role": role, "content": row['content']})

    # Panggil Service AI
    ai_response_text = generate_ai_response(
        user_message=message,
        history=history_for_ai[:-1],  # Riwayat sebelum pesan terakhir
        file_type=file_type,
        file_name=file_name
    )

    # Simpan Balasan AI
    with get_db() as conn:
        conn.execute('''
            INSERT INTO messages (chat_id, device_id, sender, content)
            VALUES (?, ?, 'assistant', ?)
        ''', (chat_id, device_id, ai_response_text))
        conn.commit()

    return jsonify({
        'success': True,
        'chat_id': chat_id,
        'user_message': {
            'sender': 'user', 
            'content': message, 
            'file_path': file_path, 
            'file_type': file_type
        },
        'assistant_message': {
            'sender': 'assistant', 
            'content': ai_response_text
        }
    })

# --- API 4: HAPUS SESI CHAT AKTIF ---
@app.route('/api/clear', methods=['POST'])
def clear_chat():
    data = request.get_json() or {}
    device_id = data.get('device_id')
    chat_id = data.get('chat_id')

    if not device_id or not chat_id:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    with get_db() as conn:
        conn.execute('DELETE FROM messages WHERE device_id = ? AND chat_id = ?', (device_id, chat_id))
        conn.execute('DELETE FROM chat_sessions WHERE device_id = ? AND chat_id = ?', (device_id, chat_id))
        conn.commit()

    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)