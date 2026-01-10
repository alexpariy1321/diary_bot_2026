import os
import asyncio
import pytz
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from groq import Groq

# 1. Загрузка конфигурации
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Твой IP и порт дашборда
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

# 3. Клавиатура (теперь это просто текстовая кнопка)
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📔 Посмотреть мой дневник")]
        ],
        resize_keyboard=True
    )
    return keyboard

# 4. Обработчики
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\nЯ записываю твои мысли в таблицу. Пиши всё, что на уме!",
        reply_markup=get_main_keyboard()
    )

# Обработка нажатия на кнопку "Посмотреть мой дневник"
@dp.message(F.text == "📔 Посмотреть мой дневник")
async def send_dashboard_link(message: types.Message):
    user_url = f"{DASHBOARD_URL}/?user_id={message.from_user.id}"
    await message.answer(f"Твоя статистика и записи доступны здесь:\n{user_url}")

@dp.message(F.text)
async def message_handler(message: types.Message):
    user = message.from_user
    text = message.text
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # ИСПРАВЛЕНО: Актуальная модель Groq
                # Запрос к Groq с новой системной ролью
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Ты — психолог-гуманист. Твоя задача — только мягкая поддержка, "
                        "никаких консультаций и решений проблем. На любые вопросы отвечай "
                        "исключительно с точки зрения психологии. "
                        "Строгое ограничение: не более 2 предложений. Отвечай на русском."
                    )
                },
                {"role": "user", "content": text},
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=100  # Дополнительная страховка длины
        )
        reply = completion.choices[0].message.content


        # Время по МСК
        msk_tz = pytz.timezone('Europe/Moscow')
        now_msk = datetime.now(msk_tz).strftime("%Y-%m-%d %H:%M:%S")

        # Запись в таблицу
        row = [now_msk, str(user.id), user.username or "", user.full_name, text, "", "", reply]
        sheet.append_row(row)

        await message.answer(reply, reply_markup=get_main_keyboard())

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("Запись сохранена, но нейросеть сейчас отдыхает.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

