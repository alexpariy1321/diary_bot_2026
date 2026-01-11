import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px

# --- 1. НАСТРОЙКА СТРАНИЦЫ И СТИЛЯ 2026 ---
st.set_page_config(page_title="Мой Дневник 2026", page_icon="📔", layout="wide")

st.markdown("""
<style>
    /* Футуристичный фон */
    .stApp {
        background: radial-gradient(circle at top right, #0a0a12, #111122, #00050a);
        color: #e0e0e0;
    }

    /* Glassmorphism для карточек */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(0, 210, 255, 0.2) !important;
        border-radius: 16px !important;
        margin-bottom: 12px !important;
        transition: all 0.4s ease;
    }
    
    div[data-testid="stExpander"]:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(0, 210, 255, 0.6) !important;
        box-shadow: 0px 0px 25px rgba(0, 210, 255, 0.2);
    }

    /* Неоновые градиентные заголовки */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Стильные метрики */
    [data-testid="stMetric"] {
        background: rgba(0, 210, 255, 0.05);
        border-radius: 12px;
        padding: 15px !important;
        border: 1px solid rgba(0, 210, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. ЛОГИКА ЗАГРУЗКИ ДАННЫХ ---
@st.cache_data(ttl=60)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("English_Bot_2026").sheet1 
    all_values = sheet.get_all_values()
    
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:])
        df.columns = ['timestamp', 'user_id', 'username', 'full_name', 'text', 'mood', 'context', 'bot_reply']
        return df
    return pd.DataFrame()

# --- 3. ОТОБРАЖЕНИЕ ИНТЕРФЕЙСА ---
try:
    df = load_data()
    user_id_param = st.query_params.get("user_id", None)

    if user_id_param and not df.empty:
        df['user_id'] = df['user_id'].astype(str)
        user_df = df[df['user_id'] == str(user_id_param)]

        if not user_df.empty:
            st.title(f"АНАЛИЗ ДНЕВНИКА: {user_df.iloc[0]['full_name']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Всего записей", len(user_df))
            
            # --- КИБЕРПАНК ГРАФИК ---
            user_df['timestamp'] = pd.to_datetime(user_df['timestamp'], errors='coerce')
            daily_counts = user_df.groupby(user_df['timestamp'].dt.date).size().reset_index(name='count')
            
            fig = px.line(daily_counts, x='timestamp', y='count', title="АКТИВНОСТЬ НЕЙРОНОВ")
            fig.update_traces(line_color='#00d2ff', line_width=4, mode='lines+markers', marker=dict(size=10))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#00d2ff"),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- СПИСОК ЗАПИСЕЙ ---
            st.subheader("АРХИВ МЫСЛЕЙ")
            for _, row in user_df.sort_values(by='timestamp', ascending=False).iterrows():
                with st.expander(f"🔹 {row['timestamp']} | {row['text'][:40]}..."):
                    st.write(f"**МЫСЛЬ:** {row['text']}")
                    if row['bot_reply']:
                        st.info(f"🧬 **ОТВЕТ ПСИХОЛОГА:** {row['bot_reply']}")
        else:
            st.warning("В базе данных пока нет ваших записей.")
    else:
        st.info("Пожалуйста, используйте кнопку в Telegram-боте для входа.")

except Exception as e:
    st.error(f"Критический сбой системы: {e}")
