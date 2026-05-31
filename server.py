import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

POINTS_NAMES = {
    1: "Hörbranz A14", 2: "Nuziders A14", 3: "Rabfeld A12", 4: "Kundl A12", 5: "Wels A8", 
    6: "Wolfsbach A1 (1)", 7: "Wolfsbach A1 (2)", 8: "Mistelbach A5", 9: "Bruck an der Leitha A4",
    10: "Pernau A2", 11: "Strass in Steiermark A9", 12: "Hainburg A2", 13: "Arnoldstein A2",
    14: "Grassbrunn A99", 15: "Eberstalzell A1", 16: "Toplitsch/Sud A10", 17: "Kuchl A10",
    18: "San Vittore A13", 19: "Holztraume A13", 20: "Erstfeld A2", 21: "Giornoco A2"
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, text TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

init_db()

# Функція-помічник для відправки в ТГ з логуванням
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        print(f"DEBUG: Відповідь ТГ: {response.status_code}, {response.text}") # ЦЕ ПОКАЖЕ ПОМИЛКУ В ЛОГАХ
        return response.status_code == 200
    except Exception as e:
        print(f"DEBUG: Помилка запиту до ТГ: {e}")
        return False

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
        cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (point_id, status, now))
        if user_id > 0:
            cursor.execute('INSERT INTO user_votes (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)', (user_id, username, first_name, now))
        conn.commit()
        conn.close()
        
        if status == 'red':
            point_name = POINTS_NAMES.get(int(point_id), f"ID {point_id}")
            tg_user = f"@{username}" if username else f"ID: {user_id}"
            msg = f"🚨 *Увага! КОНТРОЛЬ*\n\n📍 *Де:* {point_name}\n👤 *Водій:* {first_name} ({tg_user})"
            send_telegram_message(msg)
            
        return jsonify({"status": "success", "message": "Голос враховано"})
    
    conn.close()
    return jsonify({"status": "ignored", "message": "Статус не змінився"})

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    text = data.get('text', '').strip()
    if text:
        send_telegram_message(f"💡 *Пропозиція:* {text}")
    return jsonify({"status": "success"})

# ... (інші функції залишаються як були)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
