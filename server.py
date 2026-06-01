import os
import sqlite3
import requests 
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

# ====================================================================
#   НАЛАШТУВАННЯ ТЕЛЕГРАМ-УВЕДОМЛЕНЬ ВІД ВОДІЇВ
# ====================================================================
BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"
# ====================================================================

app = Flask(__name__)
CORS(app)

# Шлях для збереження бази даних на постійний диск Render
DB_PATH = "/data/austria_map.db"

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            status TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            point_id INTEGER,
            timestamp TEXT
        )
    ''')
    # Перевірка наявності колонки point_id (якщо база вже створена)
    cursor.execute("PRAGMA table_info(user_votes)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'point_id' not in columns:
        cursor.execute('ALTER TABLE user_votes ADD COLUMN point_id INTEGER')
        
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

def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        R = 6371.0
        rad_lat1 = math.radians(float(lat1))
        rad_lon1 = math.radians(float(lon1))
        rad_lat2 = math.radians(float(lat2))
        rad_lon2 = math.radians(float(lon2))
        dlon = rad_lon2 - rad_lon1
        dlat = rad_lat2 - rad_lat1
        a = math.sin(dlat / 2)**2 + math.cos(rad_lat1) * math.cos(rad_lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return 9999.0

def generate_top_data(period="week"):
    if period == "month":
        days = 30
        title = "🏆 **ТОП-10 активних водіїв (місяць):**\n\n"
    else:
        days = 7
        title = "🏆 **ТОП-10 активних водіїв (тиждень):**\n\n"
        
    limit_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT first_name, COUNT(*) as vote_count 
        FROM user_votes 
        WHERE timestamp >= ?
        GROUP BY user_id 
        ORDER BY vote_count DESC 
        LIMIT 10
    ''', (limit_date,))
    rows = cursor.fetchall()
    conn.close()
    
    medals = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
    top_text = title
    
    if not rows:
        top_text += "Голосів ще немає. Будь першим! 🚀\n"
    else:
        for i, row in enumerate(rows):
            place = medals[i] if i < len(medals) else f"{i+1}."
            top_text += f"{place} *{row[0]}* — {row[1]} голосів\n"
            
    top_text += "\nОновлено щойно. Дякуємо за допомогу на дорогах Австрії! 🤝"
    
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "📅 За тиждень", "callback_data": "top_week"},
                {"text": "📅 За місяць", "callback_data": "top_month"}
            ]
        ]
    }
    
    return top_text, inline_keyboard

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if not update: return jsonify({"status": "ignored"}), 200
        
    if "message" in update:
        chat_id = update["message"].get("chat", {}).get("id")
        text = update["message"].get("text", "").strip()
        if text == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "Вітаємо! Відкрийте мапу.", "parse_mode": "Markdown"})
        elif text == "/top":
            top_text, reply_markup = generate_top_data("week")
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": top_text, "parse_mode": "Markdown", "reply_markup": reply_markup})
            
    elif "callback_query" in update:
        callback_query = update["callback_query"]
        callback_data = callback_query.get("data")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        message_id = callback_query.get("message", {}).get("message_id")
        
        if callback_data in ["top_week", "top_month"]:
            period = "week" if callback_data == "top_week" else "month"
            new_text, reply_markup = generate_top_data(period)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id, "message_id": message_id, "text": new_text, "parse_mode": "Markdown", "reply_markup": reply_markup
            })
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_query.get("id")})
    return jsonify({"status": "success"}), 200

@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    point_id = data.get('id')
    status = data.get('status')
    user_id = data.get('user_id', 0)
    username = data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    user_lat, user_lng = data.get('user_lat'), data.get('user_lng')
    point_lat, point_lng = data.get('point_lat'), data.get('point_lng')
    
    if not (user_lat and user_lng and point_lat and point_lng) or calculate_distance(user_lat, user_lng, point_lat, point_lng) > 2.0:
        return jsonify({"status": "error", "message": "Ви занадто далеко або GPS вимкнено!"}), 400

    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Перевірка: чи голосував користувач за цю точку за останні 15 хв
    cursor.execute('''
        SELECT timestamp FROM user_votes 
        WHERE user_id = ? AND point_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (user_id, point_id))
    
    last_vote = cursor.fetchone()
    
    # Завжди оновлюємо колір точки на мапі, щоб інші бачили
    cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (point_id, status, now.isoformat()))
    
    # Додаємо голос у статистику лише якщо пройшло 15 хв
    if not last_vote or (now - datetime.fromisoformat(last_vote[0])) > timedelta(minutes=15):
        cursor.execute('INSERT INTO user_votes (user_id, username, first_name, point_id, timestamp) VALUES (?, ?, ?, ?, ?)',
                       (user_id, username, first_name, point_id, now.isoformat()))
        msg = "Голос враховано"
    else:
        msg = "Статус оновлено (голос не зараховано, оскільки 15 хв ще не пройшло)"
            
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": msg}), 200

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
        time_passed_str = ""
        if timestamp_str:
            vote_time = datetime.fromisoformat(timestamp_str)
            diff = now - vote_time
            minutes = int(diff.total_seconds() // 60)
            time_passed_str = f"{minutes} хв. тому" if minutes < 60 else f"{minutes // 60} год. {minutes % 60} хв. тому"
            if diff > timedelta(hours=1.5): is_expired = True
        
        if is_expired:
            result[point_id] = {"color": "blue", "green": 0, "red": 0, "old_status": status, "last_time": time_passed_str}
        else:
            result[point_id] = {"color": status, "green": 1 if status == 'green' else 0, "red": 1 if status == 'red' else 0, "old_status": "", "last_time": time_passed_str}
    return jsonify(result), 200

@app.route('/top', methods=['GET'])
def get_top():
    period = request.args.get('period', 'week')
    limit_date = (datetime.now() - timedelta(days=30 if period == 'month' else 7)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, username, COUNT(*) as vote_count FROM user_votes WHERE timestamp >= ? GROUP BY user_id ORDER BY vote_count DESC LIMIT 10', (limit_date,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"first_name": r[0], "username": r[1], "votes": r[2]} for r in rows]), 200

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    cursor = sqlite3.connect(DB_PATH).cursor()
    cursor.execute('INSERT INTO feedback (user_id, username, first_name, text, timestamp) VALUES (?, ?, ?, ?, ?)', 
                   (data.get('user_id'), data.get('username'), data.get('first_name'), data.get('text'), datetime.now().isoformat()))
    cursor.connection.commit()
    cursor.connection.close()
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
