import os
import threading
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from aiogram import Bot, Dispatcher, types, F

# --- КОНФІГУРАЦІЯ ---
TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM" # Вставте сюди токен від BotFather

# --- БЛОК FLASK (Ваша статистика) ---
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
        stats[id] = {"green": 0, "red": 0}
    stats[id][status] += 1
    return jsonify(stats[id])

# --- БЛОК AIOGRAM (Логіка бота) ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ОСЬ ТУТ ВАШІ ХЕНДЛЕРИ (логіка бота)
@dp.message(F.text == "/start")
async def start_command(message: types.Message):
    await message.answer("Привіт! Я працюю на сервері Render 2026!")

@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(f"Ви написали: {message.text}")

# Функція для запуску бота у фоні
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(dp.start_polling(bot))

# Запуск потоку бота ПЕРЕД запуском Flask
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Це потрібно для локального тестування
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
