
import asyncio
import csv
import json
import pandas as pd
from src.ai.gpt_client import GPTProcessor
from processing.text_collector import SiteTextCollector
from xmlriver.api import XmlRiverApi
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SemanticModel:
    def __init__(self, xmlriver_api: XmlRiverApi, gpt_processor: GPTProcessor):
        self.xmlriver_api = xmlriver_api
        self.gpt_processor = gpt_processor

    async def get_phrases_from_url(self, url):
        html = await self.gpt_processor.fetch_html(url)
        SiteTextCollector = SiteTextCollector(html)
        cleaned_text = SiteTextCollector.clean()
        print(cleaned_text)
        categories = await self.gpt_processor.get_categories(cleaned_text)
        phrases = await self.gpt_processor.generate_phrases(categories, cleaned_text)
        return phrases

    async def get_data_from_xmlriver(self, phrases):
        semantic_core_data = []
        for phrase in phrases:
            api_response = await self.xmlriver_api.get_data(phrase)  # Асинхронный вызов
            if api_response and "content" in api_response and "includingPhrases" in api_response["content"]:
                items = api_response["content"]["includingPhrases"].get("items", [])
                for item in items:
                    semantic_core_data.append({
                        "Original Query": phrase,
                        "Phrase": item["phrase"],
                        "Monthly Views": item["number"]
                    })
        return semantic_core_data

    async def convert_to_csv(self, data, filename: str = "semantic_core.csv"):
        if not data:
            logger.info("Нет данных для записи в CSV.")
            return
        df = pd.DataFrame(data)
        df.rename(columns={"Original Query": "Original Query", "Phrase": "Phrase", "Monthly Views": "Monthly Views"}, inplace=True)
        try:
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"Данные успешно записаны в {filename}")
        except Exception as e:
            logger.error(f"Ошибка при записи в CSV: {e}")