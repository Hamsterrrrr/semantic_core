import asyncio
import streamlit as st
from src.ai.gpt_client import GPTProcessor
from processing.text_collector import clean_text, extract_text, fetch_html
from src.utils import refine_output, validate_phrases

st.set_page_config(page_title="SEO Ядро", layout="wide")
st.title("Генератор семантического ядра")

async def process_url(url):
    processor = GPTProcessor()
    
    with st.spinner("Получаем данные с сайта..."):
        html = await fetch_html(url)
    
    with st.spinner("Анализируем контент..."):
        text = extract_text(html)
        cleaned_text = clean_text(text)
        
        raw_categories = await processor.get_categories(cleaned_text[:3000])
        categories = refine_output(raw_categories)
        
        raw_phrases = await processor.generate_phrases(", ".join(categories), cleaned_text[:3000])
        phrases = [p.strip() for p in raw_phrases.split(",")]
        valid_phrases = validate_phrases(phrases, cleaned_text)
    
    return categories, valid_phrases

url = st.text_input("Введите URL сайта:", "https://mnogomeb.ru/divany/")

if st.button("Сгенерировать ядро"):
    if url:
        categories, phrases = asyncio.run(process_url(url))
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Подкатегории товаров")
            st.write("\n".join(f"- {cat.capitalize()}" for cat in categories))
        
        with col2:
            st.subheader("SEO-фразы")
            st.write("\n".join(f"- {phrase}" for phrase in phrases[:15]))
    else:
        st.error("Пожалуйста, введите корректный URL")