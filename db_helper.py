import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)

def get_db_connection():
    """Membuka koneksi ke MySQL XAMPP."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_chat_db")
    )

def create_new_chat(title="Chat Baru"):
    """Membuat sesi chat baru (+ New Chat)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (title) VALUES (%s)", (title,))
    conn.commit()
    chat_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return chat_id

def save_message(chat_id, role, content):
    """Menyimpan pesan user atau AI ke database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (%s, %s, %s)",
        (chat_id, role, content)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_chat_history(chat_id):
    """Mengambil riwayat pesan dari chat_id tertentu untuk dikirim ke OpenRouter."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT role, content FROM messages WHERE chat_id = %s ORDER BY created_at ASC",
        (chat_id,)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

def get_all_chats():
    """Mengambil semua daftar chat untuk ditampilkan di Sidebar."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM chats ORDER BY created_at DESC")
    chats = cursor.fetchall()
    cursor.close()
    conn.close()
    return chats

def delete_chat(chat_id):
    """Hapus sesi chat beserta isinya."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chats WHERE id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()