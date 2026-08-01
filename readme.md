# NexaChat — AI Chatbot (Flask + SQLite + Vanilla JS)

Aplikasi chat AI dark-mode, isolasi riwayat per perangkat, dengan dukungan
unggah foto/video/dokumen. Dibangun murni dengan Flask, SQLite, HTML/CSS/JS
vanilla (tanpa React/Vue/Tailwind).

## Struktur Proyek

```
chatbot-app/
├── app.py                 # Backend Flask & API routes
├── database.py             # Inisialisasi & query SQLite
├── ai_service.py            # Integrasi modular OpenAI / Gemini / mode lokal
├── requirements.txt
├── templates/
│   └── index.html           # Markup UI chat
├── static/
│   ├── css/style.css        # Styling dark theme
│   └── js/main.js           # Logika frontend
└── uploads/                 # Folder penyimpanan file media (otomatis dibuat)
```

## Menjalankan Secara Lokal

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Buka `http://localhost:5000` di browser. Database `chatbot.db` dan folder
`uploads/` akan dibuat otomatis saat pertama kali dijalankan.

## Mengaktifkan AI Sungguhan (opsional)

Secara default aplikasi berjalan dalam **mode simulasi lokal** (tanpa API key)
agar tetap bisa langsung dicoba. Untuk menghubungkan ke OpenAI atau Gemini,
set environment variable sebelum menjalankan `app.py`:

**OpenAI**

```bash
export AI_PROVIDER=openai
export OPENAI_API_KEY=sk-xxxxxxxx
export OPENAI_MODEL=gpt-4o-mini   # opsional, ini nilai default
```

**Google Gemini**

```bash
export AI_PROVIDER=gemini
export GEMINI_API_KEY=xxxxxxxx
export GEMINI_MODEL=gemini-1.5-flash   # opsional, ini nilai default
```

Tidak ada perubahan kode yang diperlukan — `ai_service.py` otomatis memilih
provider berdasarkan variabel ini, dan akan fallback ke mode lokal jika
terjadi kegagalan (API key kosong/tidak valid, jaringan gagal, dsb).

## Cara Kerja Isolasi Perangkat

Saat halaman pertama kali dibuka, frontend membuat `device_id` unik dengan
`crypto.randomUUID()` dan menyimpannya di `localStorage`. ID ini dikirim di
setiap permintaan API (`/api/history`, `/api/chat`, `/api/clear`), sehingga
setiap browser/perangkat hanya bisa melihat dan mengubah riwayatnya sendiri.
Menghapus `localStorage` pada perangkat tersebut akan membuat riwayat lama
tidak lagi dapat diakses dari perangkat itu (walau datanya tetap ada di
database sampai dihapus manual).

## Batasan Unggahan

- Gambar: `.jpg .jpeg .png .gif .webp`
- Video: `.mp4 .webm .mov`
- Dokumen: `.pdf .txt .doc .docx .csv .md`
- Ukuran maksimum per berkas: 25 MB

## Catatan Deployment

Server bawaan Flask (`app.run(...)`) hanya untuk pengembangan. Untuk
produksi, jalankan lewat WSGI server seperti Gunicorn, misalnya:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
