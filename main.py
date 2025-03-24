"""
Главный модуль программы
"""
import asyncio
import logging
import sys
import os
import glob
from config import (
    XMLRIVER_USER_ID, 
    XMLRIVER_API_KEY, 
    XMLRIVER_BASE_URL,
    LOG_LEVEL,
    LOG_FORMAT,
    DEFAULT_OUTPUT_FILE
)
from semantic_core import SemanticModel
from src.ai.gpt_client import GPTProcessor
from src.api.xmlriver_api import XmlRiverApi

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

def cleanup_temp_files():
    """
    Очищает временные файлы, созданные во время работы программы
    """
    patterns = [
        "response_*.html", 
        "response_*.json", 
        "alt_response_*.html", 
        "alt_response_*.json",
        "test_data_*.json",
        "error_response_*.txt"
    ]
    
    total_removed = 0
    for pattern in patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                os.remove(file)
                total_removed += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file}: {str(e)}")
    
    if total_removed > 0:
        logger.info(f"Удалено {total_removed} временных файлов")

async def main():
    """
    Основная функция программы
    """
    try:
        # Получаем URL из аргументов командной строки или используем значение по умолчанию
        url = sys.argv[1] if len(sys.argv) > 1 else "https://www.divan.ru/"
        
        # Инициализация с использованием конфигурации
        logger.info("Инициализация API клиентов...")
        xmlriver_api = XmlRiverApi(
            user_id=XMLRIVER_USER_ID,
            api_key=XMLRIVER_API_KEY,
            base_url=XMLRIVER_BASE_URL
        )
        gpt_processor = GPTProcessor()
        semantic_model = SemanticModel(xmlriver_api, gpt_processor)

        # Обработка URL
        logger.info(f"Начинаем обработку URL: {url}")
        
        # Устанавливаем таймаут для всей операции
        results = await asyncio.wait_for(
            semantic_model.process_url(url),
            timeout=300  # 5 минут таймаут
        )

        # Сохранение результатов
        if results:
            logger.info(f"Получены результаты: {len(results)} категорий")
            await semantic_model.save_results(results, DEFAULT_OUTPUT_FILE)
            logger.info(f"Обработка завершена успешно. Результаты сохранены в {DEFAULT_OUTPUT_FILE}")
        else:
            logger.error("Не удалось получить результаты")
    
    except asyncio.TimeoutError:
        logger.error("Превышено время ожидания (5 минут). Операция прервана.")
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
    finally:
        # Очищаем временные файлы в конце работы
        cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main())