import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# База даних створюється в тій же папці
DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Таблиця голосів за точки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            status TEXT,
            timestamp TEXT
        )
    ''')
    # Таблиця для рейтингу водіїв
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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
    
    # Оновлюємо статус точки
    cursor.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', 
                   (point_id, status, now))
    
    # Якщо голосував реальний користувач із Телеграму, записуємо в рейтинг
    if user_id > 0:
        cursor.execute('INSERT INTO user_votes (user_id, username, first_name, timestamp) VALUES (?, ?, ?, ?)',
                       (user_id, username, first_name, now))
        
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, status FROM votes')
    rows = cursor.fetchall()
    conn.close()
    
    result = {}
    for row in rows:
        # Повертаємо формат, який очікує мапа
        green_count = 1 if row[1] == 'green' else 0
        red_count = 1 if row[1] == 'red' else 0
        result[str(row[0])] = {
            "color": row[1],
            "green": green_count,
            "red": red_count
        }
    return jsonify(result)

@app.route('/top', methods=['GET'])
def get_top():
    period = request.args.get('period', 'week')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Визначаємо фільтр по часу
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
    return jsonify(top_list)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
