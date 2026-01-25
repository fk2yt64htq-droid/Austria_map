from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Статуси точок
stats = {}  # приклад: { "5": {"green": 1, "red": 0, "last_change": datetime_obj, "status": "green"} }

# Час до синього (в хвилинах)
BLUE_DELAY = 30

@app.route("/stats", methods=["GET"])
def get_stats():
    # Оновлюємо статус на синій, якщо час минув
    now = datetime.utcnow()
    for point_id, data in stats.items():
        if data["status"] in ["green", "red"]:
            if now >= data["last_change"] + timedelta(minutes=BLUE_DELAY):
                data["status"] = "blue"
    return jsonify(stats)

@app.route("/update", methods=["POST"])
def update_stats():
    data = request.json
    point_id = str(data["id"])
    new_status = data["status"]  # "green" або "red"

    now = datetime.utcnow()
    if point_id not in stats:
        stats[point_id] = {"green": 0, "red": 0, "status": new_status, "last_change": now}
    else:
        # Збільшуємо лічильник
        stats[point_id][new_status] += 1
        # Змінюємо статус і перезапускаємо таймер
        stats[point_id]["status"] = new_status
        stats[point_id]["last_change"] = now

    return jsonify(stats[point_id])

# Асинхронний цикл, який оновлює синій статус кожну хвилину
async def blue_timer_loop():
    while True:
        now = datetime.utcnow()
        for point_id, data in stats.items():
            if data["status"] in ["green", "red"]:
                if now >= data["last_change"] + timedelta(minutes=BLUE_DELAY):
                    data["status"] = "blue"
        await asyncio.sleep(60)  # перевіряємо раз на хвилину

# Запуск Flask та таймера
async def main():
    asyncio.create_task(blue_timer_loop())
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
