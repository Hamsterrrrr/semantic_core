import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from src.ai.gpt_client import GPTProcessor
from src.api.xmlriver_api import XmlRiverApi
from src.utils.formatters import save_to_csv

logger = logging.getLogger(__name__)

class SemanticModel:
    """
    Класс для работы с семантическим ядром
    """
    def __init__(self, xmlriver_api: XmlRiverApi, gpt_processor: GPTProcessor):
        self.xmlriver_api = xmlriver_api
        self.gpt_processor = gpt_processor
        self.logger = logging.getLogger(__name__)

    async def process_url(self, url: str) -> Optional[Dict[str, List[Dict]]]:
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
                logger.error("Не удалось получить текст с сайта")
                return None

            # Получаем категории и стоп-слова через GPT
            logger.info("Получение категорий и стоп-слов...")
            categories, stop_words = await self._process_categories(site_text)
            if not categories:
                logger.error("Не удалось получить категории")
                return None
            
            logger.info(f"Получены категории: {categories}")
            logger.info(f"Получены стоп-слова: {stop_words}")

            # Получаем поисковые запросы через XmlRiver API
            logger.info("Получение поисковых запросов...")
            search_queries = await self._fetch_search_queries(categories, stop_words)
            
            # Возвращаем результаты без дополнительной фильтрации
            return search_queries

        except Exception as e:
            logger.error(f"Ошибка при обработке URL {url}: {str(e)}")
            return None

    async def _fetch_site_content(self, url: str) -> Optional[str]:
        """
        Получает контент с сайта
        
        Args:
            url: URL сайта
            
        Returns:
            Текстовый контент сайта или None в случае ошибки
        """
        try:
            text = await self.gpt_processor.fetch_html(url)
            return text if text else None
        except Exception as e:
            logger.error(f"Ошибка при получении контента: {str(e)}")
            return None

    async def _process_categories(self, site_text: str) -> Tuple[List[str], List[str]]:
        """
        Обрабатывает текст сайта и получает категории и стоп-слова
        
        Args:
            site_text: Текст сайта
            
        Returns:
            Кортеж (категории, стоп-слова)
        """
        try:
            categories = await self.gpt_processor.generate_categories(site_text)
            stop_words = await self.gpt_processor.generate_stop_words(site_text)
            return categories, stop_words
        except Exception as e:
            logger.error(f"Ошибка при обработке категорий: {str(e)}")
            return [], []

    async def _fetch_search_queries(self, categories: list, stop_words: list) -> dict:
        """
        Получает поисковые запросы для каждой категории
        
        Args:
            categories: Список категорий
            stop_words: Список стоп-слов
            
        Returns:
            Словарь с запросами по категориям
        """
        try:
            queries = {}
            for category in categories:
                self.logger.info(f"Получение данных для категории '{category}'...")
                api_data = await self.xmlriver_api.get_data(category)
                
                if api_data and "content" in api_data and "includingPhrases" in api_data["content"]:
                    items = api_data["content"]["includingPhrases"].get("items", [])
                    if items:
                        # Сохраняем полные данные о запросах, включая показы
                        queries[category] = [
                            {"phrase": item.get("phrase", ""), "number": item.get("number", 0)}
                            for item in items 
                            if item.get("phrase") not in stop_words
                        ]
                        self.logger.info(f"Добавлено {len(queries[category])} запросов для категории '{category}'")
                    else:
                        queries[category] = []
                        self.logger.warning(f"Нет данных для категории '{category}'")
                else:
                    self.logger.warning(f"Некорректный ответ API для категории '{category}'")
                    queries[category] = []
                
            return queries
        except Exception as e:
            self.logger.error(f"Ошибка при получении поисковых запросов: {str(e)}")
            return {}

    async def save_results(self, results: dict, filename: str = "semantic_core_results.csv") -> bool:
        """
        Сохраняет результаты в CSV файл
        
        Args:
            results: Результаты для сохранения
            filename: Имя файла
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        return save_to_csv(results, filename)