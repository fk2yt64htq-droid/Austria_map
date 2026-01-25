from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Спільна пам'ять для всіх водіїв
db = {}

@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify(db)

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    p_id = str(data.get('id'))
    status = data.get('status')
    
    if p_id not in db:
        db[p_id] = {'green': 0, 'red': 0}
    
    if status in ['green', 'red']:
        db[p_id][status] += 1
        
    return jsonify(db[p_id])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
