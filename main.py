import asyncio
import logging

import pandas as pd
# from semantic_core import SemanticModel
from src.ai.gpt_client import GPTProcessor
from src.processing.text_collector import  SiteTextCollector
from src.utils import refine_output, validate_phrases
from xmlriver.api import XmlRiverApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# async def main():
#     try:
#         url = "https://www.divan.ru/"
#         processor = GPTProcessor()
        
        
#         # Получение HTML
#         logger.info("Загрузка HTML...")
#         html = await processor.fetch_html(url)
#         if not html:
#             logger.error("Не удалось загрузить HTML")
#             return
#         cleaner = Cleaner(html)
#         # Извлечение текста
#         logger.info("Обработка текста...")
#         cleaned_text = cleaner.clean()
#         if len(cleaned_text) < 100:
#             logger.error("Текст слишком короткий или отсутствует")
#             return
        
#         # Извлечение категорий
#         logger.info("Извлечение категорий...")
#         raw_categories = await processor.get_categories(cleaned_text[:3000])
#         categories = refine_output(raw_categories)  # Дополнительная обработка

#         # Генерация фраз
#         logger.info("Генерация SEO-фраз...")
#         raw_phrases = await processor.generate_phrases(", ".join(categories), cleaned_text[:3000])
#         phrases = validate_phrases(raw_phrases.split(","), cleaned_text)
        
#         # Вывод
#         print("\n🔍 Результаты:")
#         print("─" * 40)
#         print("📌 Категории:")
#         print("\n".join(f"- {cat.capitalize()}" for cat in categories))
#         print("\n🔑 SEO-фразы:")
#         print("\n".join(f"- {phrase}" for phrase in phrases))
#         print("─" * 40)
        
#     except Exception as e:
#         logger.error(f"Ошибка: {str(e)}")

# if __name__ == "__main__":
#     asyncio.run(main())



async def fetch_site_text(url: str) -> str:
    """
    Загружает и возвращает очищенный текст с указанного URL.
    """
    collector = SiteTextCollector()
    text = await collector.get_text(url)
    if not text:
        logger.error("Не удалось получить текст с сайта.")
    return text


async def process_gpt(site_text: str):
    """
    Получает категории и генерирует SEO‑фразы с помощью GPTProcessor.
    Возвращает кортеж (categories, seo_phrases).
    """
    gpt_processor = GPTProcessor()

    logger.info("Извлечение категорий...")
    raw_categories = await gpt_processor.get_categories(site_text)
    # categories = refine_output(raw_categories)
    logger.info(f"Извлечённые категории: {raw_categories}")

    logger.info("Генерация SEO‑фраз...")
    raw_phrases = await gpt_processor.generate_phrases(raw_categories, site_text)
    logger.info(f"Сгенерированные SEO‑фразы: {raw_phrases}")

    return raw_categories, raw_phrases


async def main():
    url = "https://www.kirpich.ru/shop/kirpich/"  # Замените на нужный URL

    site_text = await fetch_site_text(url)
    categories, seo_phrases = await process_gpt(site_text)

    api = XmlRiverApi(user_id="16705", api_key="c9fa00b3e6cebd7787b193ed2f2afb316ab931ff")
    # Создаем словарь для хранения данных по каждому запросу
    data_by_columns = {}

# Проходим по категориям и SEO-фразам
    for item in categories + seo_phrases:
        # Получаем данные от API
        api_data = await api.get_data(item)
        
        # Проверяем, что данные корректны и содержат нужные ключи
        if api_data and "content" in api_data and "includingPhrases" in api_data["content"]:
            print(f"Статистика по запросу '{item}':")
            
            # Извлекаем элементы из ответа API
            items = api_data["content"]["includingPhrases"].get("items", [])
            
            if items:
                # Формируем список данных для текущего запроса
                data_by_columns[item] = [
                    f"{entry.get('phrase', '')} (показы: {entry.get('number', 0)})"
                    for entry in items
                ]
                print(f"Добавлено {len(data_by_columns[item])} записей для '{item}'.")
            else:
                # Если данных нет, добавляем пустой список
                data_by_columns[item] = []
                print(f"Нет данных для запроса '{item}'.")
        else:
            print(f"Некорректный ответ API для запроса '{item}'.")

    # Определяем максимальную длину данных среди всех запросов
    max_length = max(len(data) for data in data_by_columns.values())

    # Дополняем данные пустыми значениями, чтобы все столбцы имели одинаковую длину
    for key in data_by_columns:
        data_by_columns[key].extend([""] * (max_length - len(data_by_columns[key])))

    # Создаем DataFrame из данных
    df = pd.DataFrame(data_by_columns)

    # Сохраняем данные в CSV
    df.to_csv("results_with_counts.csv", index=False, encoding='utf-8')
    print("Данные сохранены в 'results_with_counts.csv'.")
        
if __name__ == "__main__":
    asyncio.run(main())