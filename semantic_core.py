import asyncio
import csv
import json
import pandas as pd
from src.ai.gpt_client import GPTProcessor
from src.processing.text_collector import SiteTextCollector
from xmlriver.api import XmlRiverApi
import logging
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SemanticModel:
    def __init__(self, xmlriver_api: XmlRiverApi, gpt_processor: GPTProcessor):
        self.xmlriver_api = xmlriver_api
        self.gpt_processor = gpt_processor
        self.logger = logging.getLogger(__name__)

    async def process_url(self, url: str) -> Optional[Dict[str, List[str]]]:
        """
        Обрабатывает URL и собирает семантическое ядро
        
        Args:
            url: URL сайта для анализа
            
        Returns:
            Dictionary с категориями и релевантными запросами
        """
        try:
            # Получаем текст с сайта
            logger.info(f"Начинаем обработку URL: {url}")
            site_text = await self._fetch_site_content(url)
            if not site_text:
                return None

            # Получаем категории и стоп-слова через GPT
            categories, stop_words = await self._process_categories(site_text)
            if not categories:
                return None

            # Получаем поисковые запросы через XmlRiver API
            search_queries = await self._fetch_search_queries(categories, stop_words)
            
            # Фильтруем и валидируем результаты
            final_results = await self._validate_results(site_text, search_queries)
            
            return final_results

        except Exception as e:
            logger.error(f"Ошибка при обработке URL {url}: {str(e)}")
            return None

    async def _fetch_site_content(self, url: str) -> Optional[str]:
        """Получает контент с сайта"""
        try:
            text = await self.gpt_processor.fetch_html(url)
            return text if text else None
        except Exception as e:
            logger.error(f"Ошибка при получении контента: {str(e)}")
            return None

    async def _process_categories(self, text: str) -> tuple[list, list]:
        """Обрабатывает текст и получает категории и стоп-слова"""
        try:
            categories = await self.gpt_processor.get_categories(text[:3000])
            stop_words = await self.gpt_processor.generate_dynamic_stop_words(text)
            return categories, stop_words
        except Exception as e:
            logger.error(f"Ошибка при обработке категорий: {str(e)}")
            return [], []

    async def _fetch_search_queries(self, categories: list, stop_words: list) -> dict:
        """Получает поисковые запросы для каждой категории"""
        try:
            queries = {}
            for category in categories:
                data = await self.xmlriver_api.get_data(category)
                if data and "content" in data:
                    items = data["content"].get("includingPhrases", {}).get("items", [])
                    queries[category] = [
                        {"phrase": item["phrase"], "number": item.get("number", 0)}
                        for item in items
                        if item["phrase"] not in stop_words
                    ]
                else:
                    queries[category] = []
                    logger.warning(f"Нет данных для запроса '{category}'.")
            return queries
        except Exception as e:
            logger.error(f"Ошибка при получении поисковых запросов: {str(e)}")
            return {}

    async def _validate_results(self, site_text: str, queries: dict) -> dict:
        """Валидирует и фильтрует результаты"""
        try:
            return await self.gpt_processor.generate_end_data(site_text, queries)
        except Exception as e:
            logger.error(f"Ошибка при валидации результатов: {str(e)}")
            return {}

    async def save_results(self, results: dict, filename: str = "semantic_core_results.csv"):
        """Сохраняет результаты в CSV файл"""
        try:
            # Подготовка данных для сохранения
            data_by_columns = {}
            
            # Преобразуем данные в формат для CSV
            for category, phrases in results.items():
                data_by_columns[category] = []
                for phrase in phrases:
                    # Проверяем, есть ли информация о показах
                    if isinstance(phrase, dict) and "phrase" in phrase and "number" in phrase:
                        data_by_columns[category].append(f"{phrase['phrase']} (показы: {phrase['number']})")
                    elif isinstance(phrase, str):
                        data_by_columns[category].append(phrase)
            
            # Выравниваем длины списков для DataFrame
            max_length = max(len(data) for data in data_by_columns.values()) if data_by_columns else 0
            for key in data_by_columns:
                data_by_columns[key].extend([""] * (max_length - len(data_by_columns[key])))
            
            # Создаем DataFrame и сохраняем в CSV
            df = pd.DataFrame(data_by_columns)
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"Результаты успешно сохранены в '{filename}'.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в CSV: {str(e)}")