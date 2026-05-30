import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Дозволяє запити з будь-яких доменів (важливо для Telegram WebApp)

DB_PATH = "database.db"  # Переконайся, що шлях збігається з твоєю конфігурацією
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ТВІЙ_ТОКЕН_БОТА")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "ТВІЙ_CHAT_ID")

# Створення таблиці, якщо вона не існує
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            text TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json or {}
    user_id = data.get('user_id', 0)
    username = data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"status": "error", "message": "Текст порожній"}), 400
        
    now = datetime.now().isoformat()
    
    # 1. Надійно зберігаємо в базу даних
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (user_id, username, first_name, text, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, text, now))
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"Помилка БД: {db_err}")
        return jsonify({"status": "error", "message": "Помилка бази даних"}), 500
    
    # 2. Відправляємо сповіщення адміну (в ізольованому блоці з таймаутом)
    if BOT_TOKEN and ADMIN_CHAT_ID:
        tg_user = f"@{username}" if username else f"ID: {user_id}"
        message_text = f"💡 *Нова пропозиція від водія!*\n\n👤 *Ім'я:* {first_name} ({tg_user})\n📝 *Ідея:* {text}"
        
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": ADMIN_CHAT_ID,
                "text": message_text,
                "parse_mode": "Markdown"
            }, timeout=5)  # Таймаут 5 секунд, щоб сервер не зависав, якщо Telegram тупить
        except Exception as tg_err:
            print(f"Помилка відправки в Telegram: {tg_err}")
            # Не повертаємо помилку користувачу, бо в БД запис уже є успішним!
            
    return jsonify({"status": "success", "message": "Дякуємо за пропозицію!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
