import os
import sqlite3
import requests
import math
# Додано send_from_directory до імпорту Flask
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta

# ====================================================================
#   НАЛАШТУВАННЯ ТЕЛЕГРАМ-УВЕДОМЛЕНЬ ВІД ВОДІЇВ
# ====================================================================
BOT_TOKEN = "8328089237:AAFQLOe7G9Odj0VCqaKeNPND-veUvny7f78"
ADMIN_CHAT_ID = "1034056050"
# ====================================================================

app = Flask(__name__)
CORS(app)

# Шлях для збереження бази даних на постійний диск Render
DB_PATH = "/data/austria_map.db"

def init_db():
    # Перевіряємо, чи існує папка /data
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
    # Перевірка наявності колонки point_id
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

# ====================================================================
#   РОУТ ДЛЯ ВІДДАТІ ФАЙЛУ ЗВУКУ (ALERT.MP3)
# ====================================================================
@app.route('/alert.mp3')
def play_alert():
    # Віддаємо файл alert.mp3 прямо з головної папки проєкту
    return send_from_directory('.', 'alert.mp3')
# ====================================================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Рахує відстань у кілометрах між двома точками на Землі (Формула Гаверсину)
    """
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
        
        distance = R * c
        return distance
    except Exception:
        return 9999.0  # Якщо координати биті або порожні

# Функція для генерації тексту ТОПу та кнопок
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
        SELECT first_name, COUNT(user_id) as vote_count 
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

# ====================================================================
#   ОБРОБКА КОМАНД ТА КЛІКІВ ДЛЯ ТЕЛЕГРАМ-БОТА
# ====================================================================
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if not update:
        return jsonify({"status": "ignored"}), 200
        
    if "message" in update:
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        
        if not chat_id or not text:
            return jsonify({"status": "ignored"}), 200

        if text == "/start":
            welcome_text = (
                "👋 **Вітаємо в Driving Assistant Bot!**\n\n"
                "🛣️ Тут ви можете моніторити ситуацію на дорогах Австрії в реальному часі.\n\n"
                "🗺️ Щоб запустити інтерактивну карту, просто натисніть синю кнопку **'Відкрити мапу'** в самому низу екрана 👇"
            )
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": welcome_text,
                "parse_mode": "Markdown"
            })

        elif text == "/top":
            top_text, reply_markup = generate_top_data("week")
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": top_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            })

    elif "callback_query" in update:
        callback_query = update["callback_query"]
        callback_data = callback_query.get("data")
        callback_id = callback_query.get("id")
        
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        
        if callback_data in ["top_week", "top_month"]:
            period = "week" if callback_data == "top_week" else "month"
            new_text, reply_markup = generate_top_data(period)
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            requests.post(url, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            })
            
            url_ans = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
            requests.post(url_ans, json={"callback_query_id": callback_id})

    return jsonify({"status": "success"}), 200
# ====================================================================

@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    point_id = data.get('id')
    status = data.get('status')
    user_id = data.get('user_id', 0)
    username = data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')
    point_lat = data.get('point_lat')
    point_lng = data.get('point_lng')
    
    if user_lat and user_lng and point_lat and point_lng:
        distance = calculate_distance(user_lat, user_lng, point_lat, point_lng)
        if distance > 2.0:
            return jsonify({"status": "error", "message": f"Ви занадто далеко ({distance:.1f} км). Радіус дії 2 км!"}), 400
    else:
        return jsonify({"status": "error", "message": "Неможливо визначити геопозицію!"}), 400

    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Завжди оновлюємо статус точки (незалежно від часу голосування)
    cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', 
                   (point_id, status, now.isoformat()))
    
    # 2. Перевіряємо останній голос користувача за ЦЮ ТОЧКУ
    cursor.execute('''
        SELECT timestamp FROM user_votes 
        WHERE user_id = ? AND point_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (user_id, point_id))
    last_vote = cursor.fetchone()
    
    # 3. Додаємо голос, якщо пройшло > 15 хв
    if not last_vote or (now - datetime.fromisoformat(last_vote[0])) > timedelta(minutes=15):
        cursor.execute('''
            INSERT INTO user_votes (user_id, username, first_name, point_id, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, point_id, now.isoformat()))
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
        point_id = str(row[0])
        status = row[1]
        timestamp_str = row[2]
        
        is_expired = False
        time_passed_str = ""
        
        if timestamp_str:
            try:
                vote_time = datetime.fromisoformat(timestamp_str)
                diff = now - vote_time
                
                minutes = int(diff.total_seconds() // 60)
                if minutes < 60:
                    time_passed_str = f"{minutes} хв. тому"
                else:
                    time_passed_str = f"{minutes // 60} год. {minutes % 60} хв. тому"
                
                if diff > timedelta(hours=1.5):
                    is_expired = True
            except Exception:
                pass

        if is_expired:
            result[point_id] = {
                "color": "blue",
                "green": 0,
                "red": 0,
                "old_status": status,
                "last_time": time_passed_str
            }
        else:
            green_count = 1 if status == 'green' else 0
            red_count = 1 if status == 'red' else 0
            result[point_id] = {
                "color": status,
                "green": green_count,
                "red": red_count,
                "old_status": "",
                "last_time": time_passed_str
            }
            
    return jsonify(result), 200

@app.route('/top', methods=['GET'])
def get_top():
    period = request.args.get('period', 'week')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if period == 'month':
        limit_date = (datetime.now() - timedelta(days=30)).isoformat()
    else:
        limit_date = (datetime.now() - timedelta(days=7)).isoformat()
        
    cursor.execute('''
        SELECT first_name, username, COUNT(user_id) as vote_count 
        FROM user_votes 
        WHERE timestamp >= ?
        GROUP BY user_id 
        ORDER BY vote_count DESC 
        LIMIT 10
    ''', (limit_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    top_list = []
    for row in rows:
        top_list.append({
            "first_name": row[0],
            "username": row[1],
            "votes": row[2]
        })
    return jsonify(top_list), 200

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    user_id = data.get('user_id', 0)
    username = data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"status": "error", "message": "Текст порожній"}), 400
        
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (user_id, username, first_name, text, timestamp) 
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, text, now))
    conn.commit()
    conn.close()
    
    if BOT_TOKEN and ADMIN_CHAT_ID:
        tg_user = f"@{username}" if username else f"ID: {user_id}"
        message_text = f"💡 *Нова пропозиція від водія!*\n\n👤 *Ім'я:* {first_name} ({tg_user})\n📝 *Ідея:* {text}"
        
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": ADMIN_CHAT_ID,
                "text": message_text,
                "parse_mode": "Markdown"
            }, timeout=5)
        except Exception as e:
            print(f"Помилка відправки в ТГ: {e}")
    
    return jsonify({"status": "success", "message": "Дякуємо за пропозицію!"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
