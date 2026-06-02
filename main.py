import logging
import asyncio
import aiohttp
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
SERVER_URL = "https://austria-map.onrender.com"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- Ваші функції для ТОПу залишаються без змін ---
async def fetch_top_data(period: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/top?period={period}") as response:
                if response.status == 200: return await response.json()
        except: pass
    return None

# [Тут ваші функції generate_top_text та build_top_keyboard]

# --- ОБРОБКА КОМАНД ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    web_app_url = "https://fk2yt64htq-droid.github.io/Austria_map/"
    kb = [[types.KeyboardButton(text="Відкрити мапу", web_app=types.WebAppInfo(url=web_app_url))]]
    await message.answer("Мапа відкрита", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# --- ОСЬ ЦЕЙ БЛОК ВІДПОВІДАЄ ЗА ПРИЙОМ ПОВІДОМЛЕНЬ З КНОПКИ ---
async def handle_support(request):
    data = await request.json()
    msg_text = data.get("message", "Без тексту")
    if ADMIN_CHAT_ID:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"💡 Звернення: {msg_text}")
    return web.json_response({"status": "ok"})

async def web_server():
    app = web.Application()
    app.router.add_post('/send_support', handle_support) # Кнопка повинна стукати сюди
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

async def main():
    await web_server() # Запускаємо сервер для кнопки
    await dp.start_polling(bot) # Запускаємо бота для Telegram

if __name__ == "__main__":
    asyncio.run(main())
