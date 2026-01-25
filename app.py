from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Статуси точок
stats = {
    # приклад:
    # "5": {"green": 1, "red": 0, "last_change": datetime.now()},
    # "7": {"green": 1, "red": 2, "last_change": datetime.now()},
}

@app.route("/stats", methods=["GET"])
def get_stats():
    now = datetime.now()
    result = {}

    for id, data in stats.items():
        # Обчислюємо колір
        if "last_change" in data and now - data["last_change"] >= timedelta(minutes=30):
            color = "blue"
        elif data.get("green", 0) == data.get("red", 0):
            color = "yellow"
        elif data.get("green", 0) > data.get("red", 0):
            color = "green"
        else:
            color = "red"

        result[id] = {
            "green": data.get("green", 0),
            "red": data.get("red", 0),
            "color": color
        }

    return jsonify(result)

@app.route("/update", methods=["POST"])
def update_stats():
    data = request.json
    id = str(data["id"])
    status = data["status"]  # "green" або "red"

    if id not in stats:
        stats[id] = {"green": 0, "red": 0, "last_change": datetime.now()}

    stats[id][status] += 1
    stats[id]["last_change"] = datetime.now()  # оновлюємо час останньої зміни

    # Повертаємо оновлену точку з коліром
    now = datetime.now()
    if now - stats[id]["last_change"] >= timedelta(minutes=3):
        color = "blue"
    elif stats[id]["green"] == stats[id]["red"]:
        color = "yellow"
    elif stats[id]["green"] > stats[id]["red"]:
        color = "green"
    else:
        color = "red"

    return jsonify({"green": stats[id]["green"], "red": stats[id]["red"], "color": color})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
