import asyncio
import logging
import math
from typing import Dict, List, Optional, Tuple

from src.ai.gpt_client import GPTProcessor
from src.api.xmlriver_api import XmlRiverApi
from src.utils.formatters import save_to_csv, save_to_advanced_formats

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
            
            # Добавляем постобработку результатов
            logger.info("Выполняем анализ и обогащение данных...")
            processed_results = await self._post_process_results(search_queries, site_text)
            
            return processed_results

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

    async def _post_process_results(self, queries: Dict[str, List[Dict]], site_text: str) -> Dict[str, List[Dict]]:
        """Выполняет постобработку и ранжирование результатов"""
        try:
            processed_queries = {}
            
            for category, phrases in queries.items():
                # Фильтрация по релевантности
                relevant_phrases = self._filter_by_relevance(phrases, site_text)
                
                # Ранжирование по показам и релевантности
                ranked_phrases = self._rank_phrases(relevant_phrases)
                
                # Ограничение количества фраз (например, топ-50)
                processed_queries[category] = ranked_phrases[:50]
            
            return processed_queries
        except Exception as e:
            self.logger.error(f"Ошибка при постобработке результатов: {str(e)}")
            return queries

    def _filter_by_relevance(self, phrases: List[Dict], site_text: str) -> List[Dict]:
        """Фильтрует фразы по релевантности к тексту сайта"""
        relevant_phrases = []
        site_text_lower = site_text.lower()
        
        for phrase in phrases:
            phrase_text = phrase.get("phrase", "").lower()
            words = phrase_text.split()
            
            # Проверка, содержит ли текст сайта слова из фразы
            matched_words = sum(1 for word in words if word in site_text_lower)
            relevance_score = matched_words / len(words) if words else 0
            
            # Добавляем релевантность к фразе
            phrase["relevance"] = relevance_score
            
            # Фильтруем фразы с низкой релевантностью
            if relevance_score >= 0.3 or int(phrase.get("number", 0)) > 1000:
                relevant_phrases.append(phrase)
        
        return relevant_phrases

    def _rank_phrases(self, phrases: List[Dict]) -> List[Dict]:
        """Ранжирует фразы по комбинации показов и релевантности"""
        # Нормализация значений показов (логарифмический масштаб)
        if phrases:
            max_shows = max(int(phrase.get("number", 0)) for phrase in phrases)
            for phrase in phrases:
                shows = int(phrase.get("number", 0))
                if shows > 0 and max_shows > 0:
                    # Логарифмический масштаб для сглаживания больших различий
                    normalized_shows = math.log10(shows) / math.log10(max_shows)
                else:
                    normalized_shows = 0
                    
                # Комбинированный рейтинг (70% показы, 30% релевантность)
                phrase["rating"] = 0.7 * normalized_shows + 0.3 * phrase.get("relevance", 0)
        
        # Сортировка по рейтингу
        return sorted(phrases, key=lambda x: x.get("rating", 0), reverse=True)

    async def save_results(self, results: dict, filename: str = "semantic_core_results") -> bool:
        """Сохраняет результаты в различных форматах"""
        # Удаляем расширение из имени файла, если оно есть
        base_filename = filename.replace('.csv', '').replace('.xlsx', '')
        
        # Базовое сохранение в CSV без добавления расширения в функции
        csv_saved = save_to_csv(results, f"{base_filename}")
        
        # Расширенное сохранение в нескольких форматах
        advanced_saved = save_to_advanced_formats(results, base_filename)
        
        return csv_saved and advanced_saved