import asyncio
import json
import logging
from aiolimiter import AsyncLimiter
from g4f.client import AsyncClient
from g4f.Provider import Free2GPT
import g4f
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re

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
    Класс для работы с GPT API
    """
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Получает HTML-контент с указанного URL
        
        Args:
            url: URL для получения контента
            
        Returns:
            Текстовый контент страницы или None в случае ошибки
        """
        try:
            self.logger.info(f"Получение HTML с {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Очищаем HTML от тегов и получаем текст
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Удаляем скрипты, стили и другие ненужные элементы
                        for script in soup(["script", "style", "meta", "noscript", "iframe"]):
                            script.extract()
                        
                        # Получаем текст
                        text = soup.get_text(separator=' ', strip=True)
                        
                        # Очищаем текст от лишних пробелов
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        self.logger.info(f"Получено {len(text)} символов текста")
                        return text
                    else:
                        self.logger.error(f"Ошибка при получении HTML: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Ошибка при получении HTML: {str(e)}")
            return None

    async def generate_categories(self, text: str) -> List[str]:
        """
        Генерирует категории на основе текста сайта
        
        Args:
            text: Текст сайта
            
        Returns:
            Список категорий
        """
        try:
            self.logger.info("Отправка запроса к GPT API")
            prompt = f"""
            Проанализируй текст сайта и определи основные категории услуг или товаров, которые предлагает компания.
            Выдели 4 основных категорий.
            
            Текст сайта:
            {text[:3000]}
            
            Формат ответа: список категорий, разделенных запятыми.
            """
            
            response = await self._send_request(prompt)
            if not response:
                return []
            
            # Обрабатываем ответ - разделяем по запятым и очищаем от лишних пробелов
            categories = [cat.strip() for cat in response.split(',')]
            self.logger.info(f"Получен ответ от GPT API")
            return categories
        except Exception as e:
            self.logger.error(f"Ошибка при генерации категорий: {str(e)}")
            return []

    async def generate_stop_words(self, text: str) -> List[str]:
        """
        Генерирует стоп-слова на основе текста сайта
        
        Args:
            text: Текст сайта
            
        Returns:
            Список стоп-слов
        """
        try:
            self.logger.info("Отправка запроса к GPT API")
            prompt = f"""
            Проанализируй текст сайта и составь список стоп-слов, которые не должны использоваться в SEO-запросах.
            Включи в список:
            1. Общие слова, не имеющие отношения к тематике сайта
            2. Слова-паразиты
            3. Технические термины, не интересные пользователям
            4. Названия городов (кроме Москвы)
            
            Текст сайта:
            {text[:3000]}
            
            Формат ответа: список стоп-слов, разделенных запятыми.
            """
            
            response = await self._send_request(prompt)
            if not response:
                return []
            
            # Обрабатываем ответ - разделяем по запятым и очищаем от лишних пробелов
            stop_words = [word.strip().lower() for word in response.split(',')]
            self.logger.info(f"Получен ответ от GPT API")
            return stop_words
        except Exception as e:
            self.logger.error(f"Ошибка при генерации стоп-слов: {str(e)}")
            return []

    async def _send_request(self, prompt: str) -> Optional[str]:
        """
        Отправляет запрос к GPT API
        
        Args:
            prompt: Текст запроса
            
        Returns:
            Ответ от API или None в случае ошибки
        """
        try:
            self.logger.info("Отправка запроса к GPT API")
            
            # Используем AsyncClient с провайдером Free2GPT
            client = AsyncClient(
                provider=Free2GPT,
                timeout=120
            )
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Извлекаем текст из ответа
            if hasattr(response, 'choices') and len(response.choices) > 0:
                result = response.choices[0].message.content
                self.logger.info("Получен ответ от GPT API (AsyncClient)")
                return result
            else:
                self.logger.error("Пустой ответ от GPT API")
                return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке запроса к GPT API: {str(e)}")
            
            # Пробуем использовать альтернативный метод
            try:
                self.logger.info("Используем альтернативный метод запроса")
                return await self._generate_response("", prompt)
            except Exception as alt_e:
                self.logger.error(f"Ошибка при использовании альтернативного метода: {str(alt_e)}")
                return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Внутренний метод для получения ответа от API.
        """
        try:
            async with rate_limit:
                self.logger.info("Отправка запроса к GPT API")
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        web_search=False
                    ),
                    timeout=60  # 60 секунд таймаут
                )
                self.logger.info("Получен ответ от GPT API")
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    logger.error("Пустой ответ от API")
                    return None
        except asyncio.TimeoutError:
            logger.error("Таймаут запроса к GPT API")
            raise  # Позволяем tenacity выполнить повторную попытку
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            raise  # Позволяем tenacity выполнить повторную попытку

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

    async def generate_end_data(self, site_text: str, queries: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Фильтрует и валидирует конечные данные, сохраняя информацию о показах"""
        system_prompt = """
        Задача: Отфильтруй и структурируй поисковые запросы по категориям.
        
        Правила:
        1. Удали:
           - Нерелевантные запросы
           - Спам и мусорные запросы
           - Запросы с опечатками
           
        2. Сгруппируй запросы по категориям
        3. Оставь только коммерческие запросы
        4. Сохрани информацию о показах для каждого запроса
        
        Формат ответа (строго JSON):
        {
            "категория_1": [
                {"phrase": "запрос_1", "number": 1000},
                {"phrase": "запрос_2", "number": 500}
            ],
            "категория_2": [
                {"phrase": "запрос_3", "number": 300},
                {"phrase": "запрос_4", "number": 200}
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
                
            # Проверяем, что каждая категория содержит список словарей с phrase и number
            for category, phrases in result.items():
                if not isinstance(phrases, list):
                    self.logger.warning(f"Некорректный формат для категории {category}, преобразуем")
                    result[category] = []
                    continue
                    
                valid_phrases = []
                for phrase in phrases:
                    if isinstance(phrase, dict) and "phrase" in phrase:
                        # Если number отсутствует, берем из исходных данных или ставим 0
                        if "number" not in phrase:
                            phrase_text = phrase["phrase"]
                            # Ищем соответствующую фразу в исходных данных
                            for orig_phrase in queries.get(category, []):
                                if isinstance(orig_phrase, dict) and orig_phrase.get("phrase") == phrase_text:
                                    phrase["number"] = orig_phrase.get("number", 0)
                                    break
                            else:
                                phrase["number"] = 0
                        valid_phrases.append(phrase)
                    elif isinstance(phrase, str):
                        # Преобразуем строку в словарь
                        for orig_phrase in queries.get(category, []):
                            if isinstance(orig_phrase, dict) and orig_phrase.get("phrase") == phrase:
                                valid_phrases.append(orig_phrase)
                                break
                        else:
                            valid_phrases.append({"phrase": phrase, "number": 0})
                
                result[category] = valid_phrases
                
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
    