import os
import sqlite3
import requests  # Імпорт для відправки повідомлень в Телеграм
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

DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

def init_db():
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
            timestamp TEXT
        )
    ''')
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
    
    # Створюємо inline-кнопки під віконечком
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
        
    # --- ОБРОБКА ЗВИЧАЙНИХ ПОВІДОМЛЕНЬ (Команди) ---
    if "message" in update:
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        
        if not chat_id or not text:
            return jsonify({"status": "ignored"}), 200

        # 1. Обробка команди /start
        if text == "/start":
            welcome_text = (
                "👋 **Вітаємо в Driving Assistant Bot!**\n\n"
                "Тут ви можете моніторити ситуацію на дорогах Австрії в реальному часі.\n\n"
                "🗺️ Щоб запустити інтерактивну карту, просто натисніть синю кнопку **'Відкрити мапу'** в самому низу екрана 👇"
            )
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": welcome_text,
                "parse_mode": "Markdown"
            })

        # 2. Обробка команди /top (по замовчуванню показуємо тиждень)
        elif text == "/top":
            top_text, reply_markup = generate_top_data("week")
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": top_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            })

    # --- ОБРОБКА КЛІКІВ НА ІНЛАЙН-КНОПКИ ---
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
            
            # Редагуємо поточне повідомлення (змінюємо текст і кнопки всередині нього)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            requests.post(url, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            })
            
            # Відповідаємо телеграму, що callback оброблено (щоб кнопка не "зависала" в режимі завантаження)
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
    
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT status FROM votes WHERE id = ?', (point_id,))
    current_row = cursor.fetchone()
    
    if current_row is None or current_row[0] != status:
        cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', 
                       (point_id, status, now))
        
        if user_id > 0:
            cursor.execute('INSERT INTO user_votes (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)',
                           (user_id, username, first_name, now))
            
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Голос враховано"}), 200
    
    conn.close()
    return jsonify({"status": "ignored", "message": "Статус не змінився"}), 200

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
