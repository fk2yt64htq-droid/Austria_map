import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

# Вставте сюди ваш токен від BotFather
API_TOKEN = '8328089237:AAGsx0fWLMT292cWyrHzKgnbEYtu9qUUzAM'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Вкажіть посилання на ваш GitHub Pages, де лежить index.html
    web_app_url = "https://fk2yt64htq-droid.github.io/Austria_map/"
    
    kb = [
        [types.KeyboardButton(text="Відкрити мапу", web_app=types.WebAppInfo(url=web_app_url))]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer("Натисніть кнопку нижче, щоб відкрити мапу:", reply_markup=keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


