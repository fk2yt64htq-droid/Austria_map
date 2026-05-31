import os
import threading
import sqlite3
import requests
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Налаштування
BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"

app = Flask(__name__)
CORS(app)
DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- База даних ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, text TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- Flask Роути ---
@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    point_id, status = data.get('id'), data.get('status')
    user_id, username = data.get('user_id', 0), data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (point_id, status, now))
    if user_id > 0:
        cursor.execute('INSERT INTO user_votes (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)', (user_id, username, first_name, now))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, status, timestamp FROM votes')
    rows = cursor.fetchall()
    conn.close()
    result = {}
    now = datetime.now()
    for row in rows:
        point_id, status, timestamp_str = str(row[0]), row[1], row[2]
        is_expired = datetime.fromisoformat(timestamp_str) < (now - timedelta(hours=1.5)) if timestamp_str else True
        result[point_id] = {"color": ("blue" if is_expired else status)}
    return jsonify(result)

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    text = data.get('text', '')
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": ADMIN_CHAT_ID, "text": f"💡 Відгук: {text}"})
    return jsonify({"status": "success"})

# --- Бот ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Мапа запущена!")

def run_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
