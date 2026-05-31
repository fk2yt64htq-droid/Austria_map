import os
import sqlite3
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "PUT_YOUR_NEW_TOKEN_HERE"
ADMIN_CHAT_ID = "1034056050"

DB = "db.sqlite"

def db():
    return sqlite3.connect(DB)

@app.route("/feedback", methods=["POST"])
def feedback():

    data = request.json

    user_id = data.get("user_id", 0)
    username = data.get("username", "")
    first_name = data.get("first_name", "Driver")
    text = data.get("text", "")

    if not text:
        return jsonify({"status":"error","message":"empty"}), 400

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            text TEXT,
            time TEXT
        )
    """)

    cur.execute(
        "INSERT INTO feedback(user_id,username,first_name,text,time) VALUES (?,?,?,?,?)",
        (user_id, username, first_name, text, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

    user_info = f"@{username}" if username else f"ID:{user_id}"

    msg = f"""💡 НОВИЙ FEEDBACK

👤 {first_name}
🆔 {user_info}

📝 {text}
"""

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ADMIN_CHAT_ID,
                "text": msg
            }
        )
    except Exception as e:
        print("TG ERROR:", e)

    return jsonify({"status":"success"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
