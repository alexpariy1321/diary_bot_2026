import os
import asyncio
import pytz
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from groq import Groq

# 1. Загрузка конфигурации
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# !!! ОБЯЗАТЕЛЬНО ПОСТАВЬ СВОЙ IP ТУТ !!!
DASHBOARD_URL = "http://213.21.242.35:8501" 

# 2. Инициализация клиентов
client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
g_client = gspread.authorize(creds)
sheet = g_client.open("English_Bot_2026").sheet1

# 3. Функция клавиатуры
def get_main_keyboard(user_id):
    # Формируем URL дашборда с ID пользователя
    webapp_url = f"{DASHBOARD_URL}/?user_id={user_id}"
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📔 Открыть мой дневник",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

# 4. Обработчики
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = get_main_keyboard(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я твой личный дневник. Напиши что-нибудь!",
        reply_markup=kb
    )

@dp.message(F.text)
async def message_handler(message: types.Message):
    user = message.from_user
    text = message.text
    
    # Визуальный эффект печати
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Ответ от Groq
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — поддерживающий и мудрый друг. Отвечай кратко на русском."},
                {"role": "user", "content": text},
            ],
            model="llama3-8b-8192",
        )
        reply = completion.choices[0].message.content

        # Московское время для таблицы
        msk_tz = pytz.timezone('Europe/Moscow')
        now_msk = datetime.now(msk_tz).strftime("%Y-%m-%d %H:%M:%S")

        # Запись в таблицу (8 колонок)
        row = [
            now_msk, 
            str(user.id), 
            user.username or "", 
            user.full_name, 
            text, 
            "", "", # mood и context
            reply
        ]
        sheet.append_row(row)

        # Отправляем ответ с кнопкой Mini App
        await message.answer(reply, reply_markup=get_main_keyboard(user.id))

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("Извини, произошла ошибка при сохранении записи.")

# 5. Запуск
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

