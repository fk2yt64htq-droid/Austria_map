import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

BOT_TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
ADMIN_CHAT_ID = "1034056050"
app = Flask(__name__)
CORS(app)
DB_PATH = os.path.join(os.path.dirname(__file__), "austria_map.db")

@app.route('/feedback', methods=['POST'])
def save_feedback():
    data = request.json
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"status": "error"}), 400
        
    # Відправка в Telegram
    msg = f"💡 Відгук: {text}\n👤 Від: {data.get('first_name')}"
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={"chat_id": ADMIN_CHAT_ID, "text": msg})
                  
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
