import os, sqlite3, asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from groq import Groq

load_dotenv()
ADMIN_ID = int(os.getenv('ADMIN_ID'))
bot = Bot(token=os.getenv('API_TOKEN'))
dp = Dispatcher()
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
WEB_APP_URL = os.getenv('WEB_APP_URL')

# БД
conn = sqlite3.connect('diary.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, registered INTEGER)')
cursor.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, analysis TEXT, score INTEGER)')
conn.commit()

class Registration(StatesGroup): name = State()

def ask_ai(text):
    try:
        with open('SYSTEM-ROLE.txt', 'r', encoding='utf-8') as f: prompt = f.read().strip()
    except: prompt = "Ты помощник-психолог."
    full_prompt = f"{prompt}\n\nВ конце напиши SCORE: [число от 1 до 10]."
    chat = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": full_prompt}, {"role": "user", "content": text}],
        model="llama-3.3-70b-versatile"
    )
    return chat.choices[0].message.content

async def process_entry(user_id, text, user_name):
    analysis = ask_ai(text)
    score = 5
    if "SCORE:" in analysis:
        try: score = int(''.join(filter(str.isdigit, analysis.split("SCORE:")[1])))
        except: pass
    cursor.execute("INSERT INTO entries (user_id, text, analysis, score) VALUES (?, ?, ?, ?)", (user_id, text, analysis, score))
    conn.commit()
    await bot.send_message(ADMIN_ID, f"🔔 {user_name} ({score}/10)\n\n{analysis}")

@dp.message(F.text == "/start")
async def start(m: types.Message, state: FSMContext):
    cursor.execute("SELECT name FROM users WHERE id=?", (m.from_user.id,))
    res = cursor.fetchone()
    if res:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Дневник", web_app=WebAppInfo(url=WEB_APP_URL))]], resize_keyboard=True)
        await m.answer(f"Привет, {res[0]}!", reply_markup=kb)
    else:
        await m.answer("Как вас зовут?"); await state.set_state(Registration.name)

@dp.message(Registration.name)
async def reg_name(m: types.Message, state: FSMContext):
    cursor.execute("INSERT INTO users (id, name, registered) VALUES (?, ?, 1)", (m.from_user.id, m.text))
    conn.commit()
    await m.answer("Регистрация завершена! Пишите или шлите голос."); await state.clear()

@dp.message(F.voice | F.text)
async def handle_diary(m: types.Message):
    cursor.execute("SELECT name FROM users WHERE id=?", (m.from_user.id,))
    res = cursor.fetchone()
    if not res: return
    if m.voice:
        file = await bot.get_file(m.voice.file_id)
        await bot.download_file(file.file_path, "v.ogg")
        with open("v.ogg", "rb") as f:
            tr = groq_client.audio.transcriptions.create(file=("v.ogg", f.read()), model="whisper-large-v3-turbo")
        text = tr.text; os.remove("v.ogg")
    else: text = m.text
    await m.answer("✅ Сохранено!"); asyncio.create_task(process_entry(m.from_user.id, text, res[0]))

async def diary_handler(request):
    path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    with open(path, 'r', encoding='utf-8') as f: return web.Response(text=f.read(), content_type='text/html')

async def main():
    app = web.Application()
    app.router.add_get('/diary', diary_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    # ИСПОЛЬЗУЕМ 0.0.0.0 ЧТОБЫ ТУННЕЛЬ МОГ ДОСТУЧАТЬСЯ
    await web.TCPSite(runner, '0.0.0.0', 8085).start()
    print("🚀 Бот и Сервер запущены на 0.0.0.0:8085")
    await dp.start_polling(bot)

if __name__ == '__main__': asyncio.run(main())
