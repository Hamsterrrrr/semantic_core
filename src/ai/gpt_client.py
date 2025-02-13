import asyncio
import logging
from aiolimiter import AsyncLimiter
from g4f.client import AsyncClient
from g4f.Provider import Free2GPT
from tenacity import retry, stop_after_attempt, wait_exponential

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Лимитирование запросов: 5 запросов в секунду
rate_limit = AsyncLimiter(max_rate=5, time_period=1)

class GPTProcessor:
    """
    Класс для взаимодействия с GPT через API (используем провайдера Phind).
    """
    def __init__(self):
        self.client = AsyncClient(provider=Free2GPT)

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

    async def get_categories(self, text: str) -> list:
        """
        Извлекает подкатегории из переданного текста.
        """
        system_prompt = (
            "**Задача:** Извлеки подкатегории товаров/услуг из текста.\n"
            "**Правила:**\n"
            "- Учитывай: тип, назначение, конструкцию.\n"
            "- Примеры:\n"
            "  - Для диванов: 'диван-кровать, угловой диван, модульный диван'\n"
            "  - Для перевозок: 'грузоперевозки, пассажирские перевозки'\n"
            "**Формат:** Через запятую, без пояснений.\n"
            "**Ограничения:**\n не более 3 категорий"
        )
        user_prompt = (
            f"Текст: {text}\n\n"
            "Пример вывода:\n"
            "Подкатегории: диван угловой, диван модульный, диван с ящиком"
        )
        raw_output = await self._generate_response(system_prompt, user_prompt)
        return raw_output.split(", ") if raw_output else []

    async def generate_phrases(self, categories: list, text: str) -> list:
        """
        Генерирует  SEO-фразы для Яндекс.Вордстат на основе категорий и текста.
        """
        system_prompt = (
            "**Задача:** Сгенерируй 3 SEO-фраз для Яндекс.Вордстат.\n"
            "**Правила:**\n"
            "- Сочетай подкатегории с модификаторами (купить, цена) и гео-уточнениями (Москва, СПб).\n"
            "- Примеры:\n"
            "  - 'купить угловой диван недорого в Москве'\n"
            "  - 'грузоперевозки по России'\n"
            "**Формат:** Через запятую.\n"
            "**Ограничения:**\n"
            " - не пиши никакие комментарии выдавай только нужную информацию"
            " - не болле 3 фраз"
        )
        user_prompt = (
            f"Категории: {', '.join(categories)}\n"
            f"Текст: {text}\n\n"
            "Пример вывода:\n"
            "SEO-фразы: купить модульный диван, диван-кровать с доставкой, угловые диваны в СПб"
        )
        raw_output = await self._generate_response(system_prompt, user_prompt)
        return raw_output.split(", ") if raw_output else []
