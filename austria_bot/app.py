from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)

# Структура:
# stats = {
#   "1": {"green":1,"red":0,"last_change":datetime, "auto_color": None}
# }
stats = {}

# Функція для автоматичної зміни кольору на синій через 30 хв після останньої зміни
def auto_blue():
    while True:
        now = datetime.now()
        for id, data in stats.items():
            if "last_change" in data:
                if now - data["last_change"] >= timedelta(minutes=3):
                    data["auto_color"] = "blue"
        time.sleep(60)  # перевірка кожну хвилину

# Запускаємо таймер у фоновому потоці
threading.Thread(target=auto_blue, daemon=True).start()

@app.route("/stats", methods=["GET"])
def get_stats():
    response = {}
    for id, data in stats.items():
        # Визначаємо колір для фронтенду
        green = data.get("green", 0)
        red = data.get("red", 0)
        if "auto_color" in data and data["auto_color"] == "blue":
            color = "blue"
        else:
            if green == red and green > 0:
                color = "yellow"
            elif green > red:
                color = "green"
            elif red > green:
                color = "red"
            else:
                color = "gray"  # якщо немає голосів
        response[id] = {"green": green, "red": red, "color": color}
    return jsonify(response)

@app.route("/update", methods=["POST"])
def update_stats():
    data = request.json
    id = str(data["id"])
    status = data["status"]  # "green" або "red"

    if id not in stats:
        stats[id] = {"green": 0, "red": 0}

    stats[id][status] += 1
    stats[id]["last_change"] = datetime.now()  # оновлюємо час зміни
    stats[id]["auto_color"] = None  # скидаємо автоматичний синій

    return jsonify(stats[id])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
