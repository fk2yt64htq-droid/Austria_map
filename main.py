import logging
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Завантажуємо налаштування
load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
SERVER_URL = "https://austria-map.onrender.com"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- Функції для ТОПу ---
async def fetch_top_data(period: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/top?period={period}") as response:
                if response.status == 200: return await response.json()
        except: pass
    return None

def build_top_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="📅 За тиждень", callback_data="top_week"),
        types.InlineKeyboardButton(text="🗓️ За місяць", callback_data="top_month")
    )
    return builder.as_markup()

def generate_top_text(top_users, period_name):
    if not top_users: return f"ТОП-10 ({period_name}): поки порожньо."
    text = f"🏆 **ТОП-10 активних водіїв ({period_name}):**\n\n"
    for i, user in enumerate(top_users):
        name = user.get('first_name', 'Водій')
        votes = user.get('votes', 0)
        text += f"{i+1}. {name} — {votes} голосів\n"
    return text

# --- Обробники команд ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    web_app_url = "https://fk2yt64htq-droid.github.io/Austria_map/"
    kb = [[types.KeyboardButton(text="Відкрити мапу", web_app=types.WebAppInfo(url=web_app_url))]]
    await message.answer("👋 **Вітаємо в Driving Assistant Bot!**\n\n"
                "🛣️ Тут ви можете моніторити ситуацію на дорогах Австрії в реальному часі.\n\n"
                "🗺️ Щоб запустити інтерактивну карту, просто натисніть синю кнопку **'Відкрити мапу'** в самому низу екрана 👇", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(Command("top"))
async def top_command(message: types.Message):
    data = await fetch_top_data("week")
    await message.answer(generate_top_text(data, "тиждень"), reply_markup=build_top_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("top_"))
async def callback_top(callback: types.CallbackQuery):
    period = "week" if callback.data == "top_week" else "month"
    data = await fetch_top_data(period)
    await callback.message.edit_text(generate_top_text(data, period), reply_markup=build_top_keyboard(), parse_mode="Markdown")
    await callback.answer()

# --- ТУТ БОТ ОТРИМУЄ ПОВІДОМЛЕННЯ ВІД КНОПКИ 💡 ---
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    if ADMIN_CHAT_ID:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"💡 Звернення: {message.web_app_data.data}")
    await message.answer("Дякуємо! Повідомлення надіслано.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
