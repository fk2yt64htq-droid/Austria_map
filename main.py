import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Твій токен
API_TOKEN = '8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM'
# URL сервера на Render
SERVER_URL = "https://austria-map.onrender.com"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

async def fetch_top_data(period: str):
    """Запит ТОПу з сервера Render"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/top?period={period}") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logging.error(f"Помилка запиту до сервера: {e}")
    return None

def build_top_keyboard():
    """Кнопки під ТОПом для перемикання періоду"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="📅 За тиждень", callback_data="top_week"),
        types.InlineKeyboardButton(text="🗓️ За місяць", callback_data="top_month")
    )
    return builder.as_markup()

def generate_top_text(top_users, period_name):
    """Форматування тексту рейтингу"""
    if not top_users:
        return f"🏆 **ТОП-10 активних водіїв ({period_name}):**\n\nПоки що немає голосів за цей період. Будь першим! 🚀"
    
    text = f"🏆 **ТОП-10 активних водіїв ({period_name}):**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(top_users):
        place = medals[i] if i < 3 else f"{i+1}."
        name = user.get('first_name', 'Водій')
        username = user.get('username')
        username_str = f" (@{username})" if username else ""
        votes = user.get('votes', 0)
        
        text += f"{place} **{name}**{username_str} — {votes} голосів\n"
        
    text += "\n*Оновлено щойно. Дякуємо за допомогу на дорогах Австрії! 🤝*"
    return text

@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Посилання на твою мапу GitHub Pages
    web_app_url = "https://fk2yt64htq-droid.github.io/Austria_map/"
    
    kb = [
        [types.KeyboardButton(text="Відкрити мапу", web_app=types.WebAppInfo(url=web_app_url))]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Вітаю! Натисніть кнопку нижче, щоб відкрити мапу контролю доріг Австрії.\n\n"
        "Також ви можете переглянути рейтинг найкращих помічників за допомогою команди /top", 
        reply_markup=keyboard
    )

@dp.message(Command("top"))
async def top_command(message: types.Message):
    """Показ тижневого топу за командою /top"""
    top_data = await fetch_top_data("week")
    text = generate_top_text(top_data, "тиждень")
    await message.answer(text, parse_mode="Markdown", reply_markup=build_top_keyboard())

@dp.callback_query(lambda c: c.data in ["top_week", "top_month"])
async def top_callback_handler(callback_query: types.CallbackQuery):
    """Обробка натискання на кнопки під топом"""
    period = "week" if callback_query.data == "top_week" else "month"
    period_name = "тиждень" if period == "week" else "місяць"
    
    top_data = await fetch_top_data(period)
    text = generate_top_text(top_data, period_name)
    
    try:
        await callback_query.message.edit_text(
            text, 
            parse_mode="Markdown", 
            reply_markup=build_top_keyboard()
        )
    except Exception:
        pass
    await callback_query.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
