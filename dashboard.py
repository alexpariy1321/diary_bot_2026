import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Мой Дневник", page_icon="📔")

@st.cache_data(ttl=60)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Файл creds.json должен быть в той же папке
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    
    # Открываем твою таблицу
    sheet = client.open("English_Bot_2026").sheet1 
    
    # Читаем все значения (включая первую строку)
    all_values = sheet.get_all_values()
    
    # Если в таблице есть хоть что-то кроме заголовков
    if len(all_values) > 1:
        # Создаем DataFrame, где данные начинаются со 2-й строки
        df = pd.DataFrame(all_values[1:])
        # ПРИНУДИТЕЛЬНО называем колонки (по твоему списку)
        df.columns = [
            'timestamp', 'user_id', 'username', 'full_name', 
            'text', 'mood', 'context', 'bot_reply'
        ]
        return df
    else:
        return pd.DataFrame()

try:
    df = load_data()

    # Получаем ID из ссылки
    user_id_param = st.query_params.get("user_id", None)

    if user_id_param and not df.empty:
        # Фильтруем
        df['user_id'] = df['user_id'].astype(str)
        user_df = df[df['user_id'] == str(user_id_param)]

        if not user_df.empty:
            st.title(f"Привет, {user_df.iloc[0]['full_name']}! 👋")
            st.metric("Всего записей", len(user_df))

            # График
            user_df['timestamp'] = pd.to_datetime(user_df['timestamp'], errors='coerce')
            daily_counts = user_df.groupby(user_df['timestamp'].dt.date).size().reset_index(name='Количество')
            fig = px.bar(daily_counts, x='timestamp', y='Количество', title="Твоя активность")
            st.plotly_chart(fig, use_container_width=True)

            # Список
            st.subheader("Твои записи:")
            for _, row in user_df.sort_values(by='timestamp', ascending=False).iterrows():
                with st.expander(f"{row['timestamp']} - {row['text'][:30]}..."):
                    st.write(f"**Ты:** {row['text']}")
                    if row['bot_reply']:
                        st.info(f"🤖 **Бот:** {row['bot_reply']}")
        else:
            st.warning(f"Записей для пользователя {user_id_param} не найдено.")
    elif df.empty:
        st.info("Таблица пока пуста.")
    else:
        st.error("Добавь свой ID в адресную строку, например: ?user_id=174812505")

except Exception as e:
    st.error(f"Произошла ошибка: {e}")
