from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

stats = {}

@app.route("/stats", methods=["GET"])
def get_stats():
    return jsonify(stats)

@app.route("/update", methods=["POST"])
def update_stats():
    data = request.json
    id = str(data["id"])
    status = data["status"]
    if id not in stats:
        stats[id] = {"green":0,"red":0}
    stats[id][status] += 1
    return jsonify(stats[id])
