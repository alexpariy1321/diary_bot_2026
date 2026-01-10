import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from groq import Groq

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# Groq
client_groq = Groq(api_key=GROQ_API_KEY)

# Бот
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кнопки
MOOD_BUTTONS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="😔 тяжело", callback_data="mood:тяжело")],
    [InlineKeyboardButton(text="😠 злюсь", callback_data="mood:злюсь")],
    [InlineKeyboardButton(text="😊 ок", callback_data="mood:ок")]
])

CONTEXT_BUTTONS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💼 работа", callback_data="ctx:работа")],
    [InlineKeyboardButton(text="🏠 дом", callback_data="ctx:дом")],
    [InlineKeyboardButton(text="👥 люди", callback_data="ctx:люди")],
    [InlineKeyboardButton(text="🤷 другое", callback_data="ctx:другое")]
])

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.reply("📝 Пиши мысли, я запишу и поддержу", reply_markup=MOOD_BUTTONS)

@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text
    user = message.from_user
    
    # Получаем данные пользователя
    username = f"@{user.username}" if user.username else "нет"
    full_name = user.full_name
    
    # Groq ответ (оставляем как есть)
    try:
        completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты бот-поддержка. 1 короткое тёплое предложение без советов."},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=40
        )
        reply = completion.choices[0].message.content
    except:
        reply = "Записал мысль ✅"
    
    # В таблицу (теперь 8 колонок)
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(user.id),
        username,    # Новая колонка C
        full_name,   # Новая колонка D
        text,        # Теперь колонка E
        "",          # mood (колонка F)
        "",          # context (колонка G)
        reply        # колонка H
    ]
    sheet.append_row(row)
    
    await message.reply(reply + "\n\n💭 Как себя ощущаешь?", reply_markup=MOOD_BUTTONS)

@dp.callback_query(F.data.startswith("mood:"))
async def process_mood(callback: CallbackQuery):
    mood = callback.data.split(":", 1)[1]
    new_text = callback.message.text.split("💭")[0] + f"💭 {mood}\n\n📍 Где это проявляется наиболее заметно?"
    
    # Обновляем в таблице
    last_row = len(sheet.get_all_values())
    row_data = sheet.row_values(last_row)
    row_data[5] = mood
    sheet.update(f'A{last_row}:H{last_row}', [row_data])
    
    await callback.message.edit_text(new_text, reply_markup=CONTEXT_BUTTONS)
    await callback.answer()

@dp.callback_query(F.data.startswith("ctx:"))
async def process_context(callback: CallbackQuery):
    ctx = callback.data.split(":", 1)[1]
    new_text = callback.message.text.split("📍")[0] + f"📍 Контекст: {ctx}"
    
    # Обновляем в таблице
    last_row = len(sheet.get_all_values())
    row_data = sheet.row_values(last_row)
    row_data[6] = ctx
    sheet.update(f'A{last_row}:H{last_row}', [row_data])
    
    await callback.message.edit_text(new_text)
    await callback.answer("✅ Сохранено")

async def main():
    print("🚀 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

