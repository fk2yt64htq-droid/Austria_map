from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os

app = Flask(__name__)
CORS(app)

# Сховище для статистики
db = {}

@app.route('/stats')
def get_stats():
    # Відправляємо статистику та поточний час сервера (now)
    return jsonify({
        "stats": db, 
        "now": int(time.time())
    })

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    p_id = str(data.get('id'))
    status = data.get('status')
    
    if p_id not in db:
        db[p_id] = {'green': 0, 'red': 0, 'time': 0}
    
    if status in ['green', 'red']:
        db[p_id][status] += 1
        db[p_id]['time'] = int(time.time()) # Фіксуємо час оновлення
        
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
