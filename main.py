import logging
import asyncio
import threading
import server  # Імпортуємо твій server.py
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

API_TOKEN = '8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM'
SERVER_URL = "https://austria-map.onrender.com"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- (Тут залиш свої функції: fetch_top_data, build_top_keyboard, generate_top_text) ---
# --- (Тут залиш свої обробники: start_command, top_command, top_callback_handler) ---

async def start_flask():
    """Запуск Flask сервера"""
    server.app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

async def main():
    # Запускаємо сервер у окремому потоці
    threading.Thread(target=lambda: server.app.run(host='0.0.0.0', port=5000), daemon=True).start()
    # Запускаємо бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
