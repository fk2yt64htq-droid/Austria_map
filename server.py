from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DB_FILE = "austria_map.db"

def init_db():
    """Створення бази даних та таблиць, якщо їх немає"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Таблиця лічильників з полем color, щоб мапа працювала правильно
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            dot_id TEXT PRIMARY KEY,
            color TEXT DEFAULT 'green',
            green INTEGER DEFAULT 0,
            red INTEGER DEFAULT 0
        )
    ''')
    # Таблиця історії для підрахунку ТОПу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vote_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dot_id TEXT,
            status TEXT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            voted_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Запуск ініціалізації БД
init_db()

@app.route('/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT dot_id, color, green, red FROM stats")
    rows = cursor.fetchall()
    conn.close()
    
    # Повертаємо формат точно такий, як очікує твоя мапа
    result = {row[0]: {'color': row[1], 'green': row[2], 'red': row[3]} for row in rows}
    return jsonify(result)

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    p_id = str(data.get('id'))
    status = data.get('status')
    
    # Дані водія з Telegram Web App
    user_id = data.get('user_id', 0)
    username = data.get('username', '')
    first_name = data.get('first_name', 'Водій')
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    if status not in ['green', 'red']:
        return jsonify({"error": "Invalid status"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Перевіряємо, чи є вже така точка в базі
    cursor.execute("SELECT color, green, red FROM stats WHERE dot_id = ?", (p_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO stats (dot_id, color, green, red) VALUES (?, ?, ?, ?)", (p_id, status, 0, 0))
    
    # Оновлюємо лічильники та поточний колір точки
    cursor.execute(f"UPDATE stats SET {status} = {status} + 1, color = ? WHERE dot_id = ?", (status, p_id))
    
    # Записуємо подію в історію для рейтингу (якщо проголосував реальний юзер)
    if user_id != 0:
        cursor.execute('''
            INSERT INTO vote_history (dot_id, status, user_id, username, first_name, voted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (p_id, status, user_id, username, first_name, now_str))
        
    conn.commit()
    
    # Беремо оновлену точку для відповіді
    cursor.execute("SELECT color, green, red FROM stats WHERE dot_id = ?", (p_id,))
    updated_row = cursor.fetchone()
    conn.close()
    
    return jsonify({'color': updated_row[0], 'green': updated_row[1], 'red': updated_row[2]})

@app.route('/top', methods=['GET'])
def get_top():
    """Маршрут, з якого бот забиратиме ТОП-10 водіїв"""
    period = request.args.get('period', 'week')
    
    now = datetime.utcnow()
    if period == 'month':
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=7)
        
    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, first_name, COUNT(*) as vote_count
        FROM vote_history
        WHERE voted_at >= ?
        GROUP BY user_id
        ORDER Bars vote_count DESC
        LIMIT 10
    ''', (start_date_str,))
    
    rows = cursor.fetchall()
    conn.close()
    
    top_list = []
    for row in rows:
        top_list.append({
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "votes": row[3]
        })
        
    return jsonify(top_list)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
