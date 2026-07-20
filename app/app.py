import streamlit as st
import pandas as pd
import os

# --- 1. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Government Radar MVP", layout="wide")
st.title("🏛 Government Radar: Мониторинг законодательства")

# --- 2. ЗАГРУЗКА ДАННЫХ (Data Layer) ---
@st.cache_data
def load_data():
    # Путь к нашему CSV
    path = "data/laws/data.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df
    return None

df = load_data()

if df is not None:
    # --- 3. БОКОВАЯ ПАНЕЛЬ (Filters Layer) ---
    st.sidebar.header("🔍 Фильтры")
    
    # Фильтр по отрасли (Domain)
    all_domains = ["Все"] + sorted(df['domain'].unique().tolist())
    selected_domain = st.sidebar.selectbox("Отрасль права", all_domains)
    
    # Фильтр по субъекту (Actor)
    # Так как в actor может быть список "Bank, Insurance", мы выделим уникальные теги
    unique_actors = set()
    df['actor'].str.split(',').apply(lambda x: [unique_actors.add(i.strip()) for i in x])
    selected_actor = st.sidebar.selectbox("Кого касается (Actor)", ["Все"] + sorted(list(unique_actors)))

    # --- 4. ЛОГИКА ФИЛЬТРАЦИИ (Core Layer) ---
    filtered_df = df.copy()
    
    if selected_domain != "Все":
        filtered_df = filtered_df[filtered_df['domain'] == selected_domain]
    
    if selected_actor != "Все":
        filtered_df = filtered_df[filtered_df['actor'].str.contains(selected_actor, na=False)]

    # --- 5. ИНТЕРФЕЙС (UI Layer) ---
    st.subheader(f"Найдено изменений: {len(filtered_df)}")
    
    # Выводим данные в виде карточек
    for _, row in filtered_df.iterrows():
        with st.expander(f"📍 {row['Изменяемый закон и Статья']} | {row['Тип правки']}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.info(f"**Бизнес-суть:**\n\n{row['Бизнес-суть (Простым языком)']}")
                st.caption(f"📅 Вступает в силу: {row['Дата вступления в силу']}")
                st.caption(f"🏷 Теги: {row['actor']}")
            
            with col2:
                st.warning("**Точная цитата:**")
                st.code(row['Точная цитата (Текст нормы / инструкция)'], language=None)

    # --- 6. ЗАДЕЛ ПОД AI (AI Layer placeholder) ---
    st.divider()
    st.subheader("🤖 Спросить AI-ассистента")
    user_input = st.text_input("Введите ваш вопрос по этим законам:")
    if st.button("Проанализировать"):
        st.write("Здесь будет работать AI Router (Ollama/OpenRouter)...")

else:
    st.error("Файл данных не найден. Проверьте data/laws/data.csv")