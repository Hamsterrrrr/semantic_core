import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SiteTextCollector:
    """
    Класс для асинхронного получения и извлечения текста с веб-сайта.
    """
    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session

    async def fetch_html(self, url: str) -> str:
        """
        Загружает HTML-страницу по заданному URL.
        """
        if not self.session:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text(encoding="utf-8")
                    return html
        else:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text(encoding="utf-8")
                return html

    @staticmethod
    def extract_text(html: str) -> str:
        """
        Извлекает текст из HTML, удаляя теги script и style.
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text

    async def get_text(self, url: str) -> str:
        """
        Основной метод получения текста с сайта.
        """
        try:
            html = await self.fetch_html(url)
            text = self.extract_text(html)
            return text
        except Exception as e:
            logger.error(f"Ошибка при получении текста с {url}: {e}")
            return ""