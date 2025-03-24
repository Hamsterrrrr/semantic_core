import asyncio
import json
import logging
from config import XMLRIVER_USER_ID, XMLRIVER_API_KEY
import pandas as pd
from semantic_core import SemanticModel
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
    try:
        collector = SiteTextCollector()
        text = await collector.get_text(url)
        if not text.strip():
            logger.error("Не удалось получить или очистить текст с сайта.")
            return ""
        return text
    except Exception as e:
        logger.error(f"Ошибка при загрузке текста с сайта: {str(e)}")
        return ""


async def process_gpt(site_text: str):
    """
    Получает категории и генерирует SEO-фразы с помощью GPTProcessor.
    Возвращает кортеж (categories, stop_words).
    """
    try:
        gpt_processor = GPTProcessor()
        logger.info("Извлечение категорий...")
        raw_categories = await gpt_processor.get_categories(site_text[:3000])
        logger.info(f"Извлечённые категории: {raw_categories}")

        # Загрузка существующих стоп-слов
        logger.info("Загрузка существующих стоп-слов...")
        with open("minus.json", "r", encoding="utf-8") as f:
            minus_data = json.load(f)
            existing_stops = (
                minus_data["common_words"] +
                minus_data["rf_cities_without_moscow"] +
                minus_data["moscow_popular_cities"]
            )

        # Генерация новых стоп-слов с фильтрацией
        logger.info("Генерация динамических стоп-слов...")
        dynamic_stop_words = await gpt_processor.generate_dynamic_stop_words(
            text=site_text,
            existing_stops=existing_stops
        )
        logger.info(f"Сгенерированные стоп-слова: {dynamic_stop_words}")
        return raw_categories, dynamic_stop_words
    except Exception as e:
        logger.error(f"Ошибка при обработке GPT: {str(e)}")
        return [], []


async def fetch_api_data(api: XmlRiverApi, categories: list, stop_words: list) -> dict:
    """
    Получает данные из API XmlRiver для каждой категории.
    Возвращает словарь с данными по категориям.
    """
    data_by_columns = {}
    for item in categories:
        try:
            logger.info(f"Получение данных для категории '{item}'...")
            api_data = await api.get_data(item)

            if api_data and "content" in api_data and "includingPhrases" in api_data["content"]:
                items = api_data["content"]["includingPhrases"].get("items", [])
                if items:
                    data_by_columns[item] = [
                        f"{entry.get('phrase', '')} (показы: {entry.get('number', 0)})"
                        for entry in items if entry.get('phrase') not in stop_words
                    ]
                    logger.info(f"Добавлено {len(data_by_columns[item])} записей для '{item}'.")
                    
                else:
                    data_by_columns[item] = []
                    logger.warning(f"Нет данных для запроса '{item}'.")
            else:
                logger.warning(f"Некорректный ответ API для запроса '{item}'.")
        except Exception as e:
            logger.error(f"Ошибка при получении данных для категории '{item}': {str(e)}")
            data_by_columns[item] = []
    logger.info(f"Data by columns: {data_by_columns}")
    return data_by_columns


async def end_filter(site_text: str, end_data: dict) -> dict:
    """
    Фильтрует конечные данные с помощью GPTProcessor.
    """
    try:
        gpt_processor = GPTProcessor()
        logger.info("Фильтрация конечных данных...")
        filtered_data = await gpt_processor.generate_end_data(site_text, end_data)
        logger.info(f"Конечный результат: {filtered_data}")
        return filtered_data
    except Exception as e:
        logger.error(f"Ошибка при фильтрации конечных данных: {str(e)}")
        return {}


async def save_results_to_csv(data_by_columns: dict, filename: str = "results_with_counts.csv"):
    """
    Сохраняет результаты в CSV-файл.
    """
    try:
        max_length = max(len(data) for data in data_by_columns.values())
        for key in data_by_columns:
            data_by_columns[key].extend([""] * (max_length - len(data_by_columns[key])))

        df = pd.DataFrame(data_by_columns)
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Данные успешно сохранены в '{filename}'.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в CSV: {str(e)}")


async def main():
    # Инициализация с использованием конфигурации
    xmlriver_api = XmlRiverApi(
        user_id=XMLRIVER_USER_ID,
        api_key=XMLRIVER_API_KEY
    )
    gpt_processor = GPTProcessor()
    semantic_model = SemanticModel(xmlriver_api, gpt_processor)

    # Обработка URL
    url = "https://moscow-stom.ru/services/"  # Замените на нужный URL
    results = await semantic_model.process_url(url)

    # Сохранение результатов
    if results:
        await semantic_model.save_results(results)
    else:
        logger.error("Не удалось получить результаты")


if __name__ == "__main__":
    asyncio.run(main())