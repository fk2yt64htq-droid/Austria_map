import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

# Твої дані
BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, text TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

init_db()

@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    point_id, status = data.get('id'), data.get('status')
    user_id, username = data.get('user_id', 0), data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM votes WHERE id = ?', (point_id,))
    current_row = cursor.fetchone()
    
    if current_row is None or current_row[0] != status:
        cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (point_id, status, now))
        if user_id > 0:
            cursor.execute('INSERT INTO user_votes (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)', (user_id, username, first_name, now))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Голос враховано"})
    
    conn.close()
    return jsonify({"status": "ignored", "message": "Статус не змінився"})

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
        is_expired = False
        if timestamp_str:
            try:
                if now - datetime.fromisoformat(timestamp_str) > timedelta(hours=1.5): is_expired = True
            except: pass
        result[point_id] = {"color": ("blue" if is_expired else status), "green": (1 if status == 'green' and not is_expired else 0), "red": (1 if status == 'red' and not is_expired else 0)}
    return jsonify(result)

@app.route('/top', methods=['GET'])
def get_top():
    period = request.args.get('period', 'week')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    limit_date = (datetime.now() - timedelta(days=(30 if period == 'month' else 7))).isoformat()
    cursor.execute('SELECT first_name, username, COUNT(user_id) FROM user_votes WHERE timestamp >= ? GROUP BY user_id ORDER BY COUNT(user_id) DESC LIMIT 10', (limit_date,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"first_name": r[0], "username": r[1], "votes": r[2]} for r in rows])

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    user_id, username, first_name, text = data.get('user_id', 0), data.get('username', ''), data.get('first_name', 'Водій'), data.get('text', '').strip()
    if not text: return jsonify({"status": "error", "message": "Текст порожній"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO feedback (user_id, username, first_name, text, timestamp) VALUES (?, ?, ?, ?, ?)', (user_id, username, first_name, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Відправка в ТГ
    try:
        msg = f"💡 *Пропозиція від {first_name} (@{username}):* {text}"
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                 json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"DEBUG: Telegram response: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"DEBUG: Error sending to Telegram: {e}")
        
    return jsonify({"status": "success", "message": "Дякуємо за пропозицію!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
