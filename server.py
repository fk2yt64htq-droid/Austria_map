import os
import sqlite3
import requests
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

# ====================================================================
#   НАЛАШТУВАННЯ
# ====================================================================
BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"
DB_PATH = "/data/austria_map.db"

app = Flask(__name__)
CORS(app)

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, point_id INTEGER, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, text TEXT, timestamp TEXT)')
    
    # Додавання колонки, якщо її немає
    cursor.execute("PRAGMA table_info(user_votes)")
    if 'point_id' not in [info[1] for info in cursor.fetchall()]:
        cursor.execute('ALTER TABLE user_votes ADD COLUMN point_id INTEGER')
    conn.commit()
    conn.close()

init_db()

def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        R = 6371.0
        r1, r2, r3, r4 = math.radians(float(lat1)), math.radians(float(lon1)), math.radians(float(lat2)), math.radians(float(lon2))
        dlon, dlat = r4 - r2, r3 - r1
        a = math.sin(dlat / 2)**2 + math.cos(r1) * math.cos(r3) * math.sin(dlon / 2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    except: return 9999.0

def generate_top_data(period="week"):
    days = 30 if period == "month" else 7
    limit_date = (datetime.now() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Повернув COUNT(user_id), щоб гарантовано працювало групування
    cursor.execute('''
        SELECT first_name, COUNT(user_id) as vote_count 
        FROM user_votes 
        WHERE timestamp >= ?
        GROUP BY user_id 
        ORDER BY vote_count DESC 
        LIMIT 10
    ''', (limit_date,))
    rows = cursor.fetchall()
    conn.close()
    
    top_text = f"🏆 **ТОП-10 активних водіїв ({'місяць' if period == 'month' else 'тиждень'}):**\n\n"
    if not rows: top_text += "Голосів ще немає. Будь першим! 🚀\n"
    else:
        for i, row in enumerate(rows):
            top_text += f"{i+1}. *{row[0]}* — {row[1]} голосів\n"
    
    inline_keyboard = {"inline_keyboard": [[{"text": "📅 Тиждень", "callback_data": "top_week"}, {"text": "📅 Місяць", "callback_data": "top_month"}]]}
    return top_text, inline_keyboard

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if "callback_query" in update:
        cq = update["callback_query"]
        cd, chat_id, mid = cq.get("data"), cq["message"]["chat"]["id"], cq["message"]["message_id"]
        if cd in ["top_week", "top_month"]:
            text, markup = generate_top_data("week" if cd == "top_week" else "month")
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id": chat_id, "message_id": mid, "text": text, "parse_mode": "Markdown", "reply_markup": markup})
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
    return jsonify({"status": "success"}), 200

@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    pid, status, uid, un, fn = data.get('id'), data.get('status'), data.get('user_id'), data.get('username'), data.get('first_name')
    if calculate_distance(data.get('user_lat'), data.get('user_lng'), data.get('point_lat'), data.get('point_lng')) > 2.0:
        return jsonify({"status": "error", "message": "Далеко!"}), 400
    
    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp FROM user_votes WHERE user_id = ? AND point_id = ? ORDER BY timestamp DESC LIMIT 1', (uid, pid))
    last = cursor.fetchone()
    cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (pid, status, now.isoformat()))
    
    if not last or (now - datetime.fromisoformat(last[0])) > timedelta(minutes=15):
        cursor.execute('INSERT INTO user_votes (user_id, username, first_name, point_id, timestamp) VALUES (?, ?, ?, ?, ?)', (uid, un, fn, pid, now.isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.cursor().execute('SELECT id, status, timestamp FROM votes').fetchall()
    conn.close()
    res, now = {}, datetime.now()
    for r in rows:
        diff = now - datetime.fromisoformat(r[2])
        res[str(r[0])] = {"color": "blue" if diff > timedelta(hours=1.5) else r[1], "green": 1 if r[1]=='green' and diff < timedelta(hours=1.5) else 0, "red": 1 if r[1]=='red' and diff < timedelta(hours=1.5) else 0}
    return jsonify(res), 200

@app.route('/top', methods=['GET'])
def get_top():
    period = request.args.get('period', 'week')
    limit = (datetime.now() - timedelta(days=30 if period == 'month' else 7)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.cursor().execute('SELECT first_name, username, COUNT(user_id) FROM user_votes WHERE timestamp >= ? GROUP BY user_id ORDER BY COUNT(user_id) DESC LIMIT 10', (limit,)).fetchall()
    conn.close()
    return jsonify([{"first_name": r[0], "username": r[1], "votes": r[2]} for r in rows]), 200

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute('INSERT INTO feedback (user_id, username, first_name, text, timestamp) VALUES (?, ?, ?, ?, ?)', (data.get('user_id'), data.get('username'), data.get('first_name'), data.get('text'), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": ADMIN_CHAT_ID, "text": f"💡 *Відгук:* {data.get('text')}", "parse_mode": "Markdown"})
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
