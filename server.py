import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"

app = Flask(__name__)
CORS(app)
DB_PATH = "austria_map.db"

@app.route('/update', methods=['POST'])
def update_point():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT OR REPLACE INTO votes (id, status, timestamp) VALUES (?, ?, ?)', (data['id'], data['status'], datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/feedback', methods=['POST'])
def save_feedback():
    text = request.json.get('text', '')
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      json={"chat_id": ADMIN_CHAT_ID, "text": f"Відгук: {text}"})
    except: pass
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
