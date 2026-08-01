"""
ai_service.py
Modul modular untuk menghasilkan respons AI.

Mendukung tiga provider (diatur lewat environment variable AI_PROVIDER):
  - "openai" : menggunakan OpenRouter / OpenAI API (butuh OPENAI_API_KEY)
  - "gemini" : menggunakan Google Gemini API (butuh GEMINI_API_KEY)
  - "local"  : mode simulasi/fallback tanpa API key eksternal (default)
"""

import os
import random
import json
import urllib.request
import urllib.error

# 1. Import load_dotenv secara aman (Aman untuk Vercel & Lokal)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # Di Vercel environment variables dibaca otomatis dari Dashboard Settings

# 2. Ambil environment variables
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# 3. Print Debugging
print("====================================")
print(f"[DEBUG] AI Provider aktif: {AI_PROVIDER}")
print(f"[DEBUG] OpenAI API Key terdeteksi: {bool(OPENAI_API_KEY)}")
print(f"[DEBUG] Gemini API Key terdeteksi: {bool(GEMINI_API_KEY)}")
print("====================================")


def generate_ai_response(user_message, history=None, file_type=None, file_name=None):
    """
    Titik masuk tunggal untuk menghasilkan balasan AI.
    Disesuaikan agar menerima parameter 'history' dari app.py.
    """
    try:
        if AI_PROVIDER == "openai" and OPENAI_API_KEY:
            return _generate_openai(user_message, history, file_type, file_name)
        if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
            return _generate_gemini(user_message, history, file_type, file_name)
            
    except Exception as exc:
        # TAMPILKAN DETAIL ERROR ASLI DI LOGS TERMINAL / VERCEL
        print("\n=================== DETEKSI ERROR AI ===================")
        print(f"Provider yang digunakan : {AI_PROVIDER}")
        print(f"Pesan Error Asli        : {exc}")
        print("========================================================\n")

    # Jika API Gagal/Gagal Auth/Tanpa Key, akan jatuh ke fallback ini
    return _generate_local(user_message, file_type, file_name)


def _generate_openai(user_message, history=None, file_type=None, file_name=None):
    """Integrasi OpenRouter / OpenAI dengan Memori Riwayat Chat."""
    
    messages = [
        {"role": "system", "content": "Kamu adalah asisten AI yang ramah, membantu, dan menjawab dalam bahasa yang sama dengan pengguna."}
    ]

    # 1. Masukkan riwayat pesan lama dari database ke request API
    if history and isinstance(history, list):
        messages.extend(history)

    # 2. Pesan terbaru dari pengguna
    prompt = user_message or ""
    if file_name:
        prompt += f"\n\n[Pengguna turut melampirkan berkas: {file_name} ({file_type})]"

    messages.append({"role": "user", "content": prompt or "Halo"})

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "HTTP-Referer": "https://vercel.com",  # Header wajib untuk OpenRouter
            "X-Title": "My AI App",
        },
        method="POST",
    
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    

def _generate_gemini(user_message, history=None, file_type=None, file_name=None):
    """Integrasi dengan Google Gemini API."""
    prompt = user_message or ""
    if file_name:
        prompt += f"\n\n[Pengguna turut melampirkan berkas: {file_name} ({file_type})]"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt or "Halo"}]}]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _generate_local(user_message, file_type=None, file_name=None):
    """
    Mode simulasi lokal (fallback default) — tidak membutuhkan API key.
    """
    text = (user_message or "").strip()

    if file_name and not text:
        return (
            f"Saya menerima berkas **{file_name}**. "
            f"Saat ini saya berjalan dalam mode simulasi lokal."
        )

    if file_name and text:
        return (
            f"Terima kasih atas pesannya beserta berkas **{file_name}**.\n\n"
            f"> {text}"
        )

    if not text:
        return "Sepertinya pesan Anda kosong. Coba ketik sesuatu, ya! 🙂"

    greetings = ["hai", "halo", "hi", "hello", "pagi", "malam", "siang", "sore"]
    if any(text.lower().startswith(g) for g in greetings):
        return random.choice([
            "Halo! Ada yang bisa saya bantu hari ini?",
            "Hai! Senang bisa mengobrol denganmu. Ada yang ingin ditanyakan?",
            "Halo juga! Silakan sampaikan pertanyaan atau topik yang ingin kamu bahas.",
        ])

    return f"Saya menerima pesan Anda:\n\n> {text}"