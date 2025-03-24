import asyncio
import json
import logging
from aiolimiter import AsyncLimiter
from g4f.client import AsyncClient
from g4f.Provider import Free2GPT
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(lineno)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Лимитирование запросов: 5 запросов в секунду
rate_limit = AsyncLimiter(max_rate=5, time_period=1)

class GPTProcessor:
    """
    Класс для взаимодействия с GPT через API (используем провайдера Free2GPT).
    """
    def __init__(self):
        self.client = AsyncClient(provider=Free2GPT)
        self.logger = logging.getLogger(__name__)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Внутренний метод для получения ответа от API.
        """
        try:
            async with rate_limit:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    web_search=False
                )
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    logger.error("Пустой ответ от API")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            raise  # Позволяем tenacity выполнить повторную попытку

    async def fetch_html(self, url: str) -> Optional[str]:
        """Получает HTML-контент с указанного URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении HTML: {str(e)}")
            return None

    async def get_categories(self, text: str) -> List[str]:
        """Извлекает категории из текста с помощью GPT"""
        system_prompt = """
        Задача: Проанализируй текст и выдели основные категории товаров/услуг.
        
        Правила:
        1. Выдели 3-5 основных категорий
        2. Используй существительные в именительном падеже
        3. Категории должны быть конкретными (например: "кухонные столы", а не просто "мебель")
        
        Формат вывода: список через запятую
        Пример: кухонные столы, офисные стулья, журнальные столики
        """
        
        user_prompt = f"Текст для анализа: {text[:1500]}"  # Ограничиваем длину текста
        
        response = await self._generate_response(system_prompt, user_prompt)
        if not response:
            return []
            
        categories = [cat.strip() for cat in response.split(',') if cat.strip()]
        return categories[:5]  # Ограничиваем количество категорий

    async def generate_dynamic_stop_words(self, text: str, existing_stops: List[str] = None) -> List[str]:
        """Генерирует стоп-слова на основе контекста"""
        system_prompt = """
        Задача: Сгенерируй минус-слова для поисковой рекламы.
        
        Правила:
        1. Исключи:
           - Нерелевантные услуги (ремонт, аренда)
           - Б/У товары
           - Географические названия
           - Маркетплейсы (авито, юла)
           
        2. Используй существительные в именительном падеже
        
        Формат: список через запятую
        Пример для мебели: ремонт, аренда, б/у, авито, юла, доставка
        """
        
        user_prompt = f"Товар/услуга: {text[:500]}"
        
        response = await self._generate_response(system_prompt, user_prompt)
        if not response:
            return []
            
        new_words = [word.strip().lower() for word in response.split(',') if word.strip()]
        
        if existing_stops:
            new_words = self.filter_duplicates(new_words, existing_stops)
            
        return new_words

    async def generate_end_data(self, site_text: str, queries: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Фильтрует и валидирует конечные данные"""
        system_prompt = """
        Задача: Отфильтруй и структурируй поисковые запросы по категориям.
        
        Правила:
        1. Удали:
           - Нерелевантные запросы
           - Спам и мусорные запросы
           - Запросы с опечатками
           
        2. Сгруппируй запросы по категориям
        3. Оставь только коммерческие запросы
        
        Формат ответа (строго JSON):
        {
            "категория_1": [
                "запрос_1",
                "запрос_2"
            ],
            "категория_2": [
                "запрос_3",
                "запрос_4"
            ]
        }
        """
        
        user_prompt = f"""
        Контекст: {site_text[:1000]}
        Данные для обработки: {json.dumps(queries, ensure_ascii=False)}
        """
        
        response = await self._generate_response(system_prompt, user_prompt)
        if not response:
            return {}
            
        try:
            # Извлекаем JSON из ответа
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                self.logger.error("Не найдена JSON структура в ответе")
                return {}
                
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            
            # Валидация структуры
            if not isinstance(result, dict):
                self.logger.error("Некорректная структура JSON")
                return {}
                
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка парсинга JSON: {e}")
            return {}

    @staticmethod
    def filter_duplicates(new_words: list, existing_stops: list) -> list:
        """
        Фильтрует дубликаты и подстроки в новых стоп-словах.
        """
        normalized_existing = {word.strip().lower() for word in existing_stops}
        filtered = [
            word for word in new_words
            if word.strip().lower() not in normalized_existing
            and not any(exist in word.lower() for exist in normalized_existing)
        ]
        return filtered
    