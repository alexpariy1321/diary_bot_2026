import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread

load_dotenv()
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")

print("Проверяем credentials...")
creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=[
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
])
client = gspread.authorize(creds)
print("✅ Авторизация прошла!")
print("Мои таблицы:")
for sheet in client.list_spreadsheet_files():
    print(f"  - {sheet['name']} (ID: {sheet['id']})")
