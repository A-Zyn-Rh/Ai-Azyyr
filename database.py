"""
database.py
Modul untuk inisialisasi dan pengelolaan database SQLite pada AI Chatbot.
Menangani skema tabel `sessions` dan `messages`, serta menyediakan fungsi
query yang digunakan oleh app.py.
"""

import sqlite3
import os
from datetime import datetime, timezone

# Lokasi file database SQLite (berada satu folder dengan app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chatbot.db")


def get_db_connection():
    """
    Membuka koneksi baru ke database SQLite.
    row_factory diset ke sqlite3.Row agar hasil query bisa diakses
    seperti dictionary (mis. row["content"]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Aktifkan foreign key constraint (SQLite mematikannya secara default)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Inisialisasi skema database. Dipanggil sekali saat aplikasi Flask start.
    Aman dipanggil berulang kali karena menggunakan CREATE TABLE IF NOT EXISTS.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                device_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user', 'assistant')),
                content TEXT,
                file_path TEXT,
                file_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES sessions (device_id)
            )
        """)

        # Index untuk mempercepat query riwayat per device_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_device_id
            ON messages (device_id, timestamp)
        """)

        conn.commit()
        print(f"[database] Database siap di: {DB_PATH}")
    finally:
        conn.close()


def ensure_session(device_id):
    """
    Memastikan device_id terdaftar di tabel sessions.
    Jika belum ada, buat baris baru. Idempotent (aman dipanggil berkali-kali).
    """
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (device_id) VALUES (?)",
            (device_id,)
        )
        conn.commit()
    finally:
        conn.close()


def add_message(device_id, sender, content=None, file_path=None, file_type=None):
    """
    Menyimpan satu pesan baru ke tabel messages.
    Mengembalikan dictionary representasi pesan yang baru disimpan,
    termasuk id dan timestamp yang dihasilkan oleh database.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (device_id, sender, content, file_path, file_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (device_id, sender, content, file_path, file_type)
        )
        conn.commit()
        new_id = cursor.lastrowid

        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (new_id,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def get_history(device_id):
    """
    Mengambil seluruh riwayat pesan untuk device_id tertentu,
    diurutkan dari yang paling lama ke paling baru.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, device_id, sender, content, file_path, file_type, timestamp
            FROM messages
            WHERE device_id = ?
            ORDER BY id ASC
            """,
            (device_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def clear_history(device_id):
    """
    Menghapus seluruh riwayat pesan milik device_id tertentu.
    Baris sesi (sessions) tetap dipertahankan agar device_id tetap valid.
    Mengembalikan daftar file_path yang terkait agar file fisik juga
    bisa dihapus oleh pemanggil (app.py) jika diinginkan.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT file_path FROM messages WHERE device_id = ? AND file_path IS NOT NULL",
            (device_id,)
        ).fetchall()
        file_paths = [row["file_path"] for row in rows]

        conn.execute("DELETE FROM messages WHERE device_id = ?", (device_id,))
        conn.commit()
        return file_paths
    finally:
        conn.close()