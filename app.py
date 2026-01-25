import os
import threading
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- КОНФІГУРАЦІЯ ---
TOKEN = "8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM"
WEB_APP_URL = "https://fk2yt64htq-droid.github.io"

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
    user_id = str(data["id"])
    status = data["status"]
    if user_id not in stats:
        stats[user_id] = {"green": 0, "red": 0}
    stats[user_id][status] += 1
    return jsonify(stats[user_id])

# --- БЛОК AIOGRAM (Логіка бота з кнопкою мапи) ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Відкрити мапу", web_app=types.WebAppInfo(url=WEB_APP_URL))]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Натисніть кнопку нижче, щоб відкрити мапу:", reply_markup=keyboard)

# Функція для запуску бота у фоновому потоці
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Запускаємо polling
    loop.run_until_complete(dp.start_polling(bot))

# Запускаємо потік з ботом паралельно з Flask
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Це потрібно для локального запуску, Render використає gunicorn
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
