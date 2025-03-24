"""
Конфигурационный файл проекта
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# API ключи
XMLRIVER_USER_ID = os.getenv("XMLRIVER_USER_ID", "16705")
XMLRIVER_API_KEY = os.getenv("XMLRIVER_API_KEY", "c9fa00b3e6cebd7787b193ed2f2afb316ab931ff")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(lineno)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки API
XMLRIVER_BASE_URL = "http://xmlriver.com/wordstat/new/json"
GPT_MODEL = "gpt-4o-mini"

# Настройки вывода
DEFAULT_OUTPUT_FILE = "semantic_core_results.csv"

# Настройки отладки
SAVE_DEBUG_FILES = os.getenv("SAVE_DEBUG_FILES", "False").lower() == "true"

# Проверка наличия необходимых переменных
if not all([XMLRIVER_USER_ID, XMLRIVER_API_KEY]):
    raise ValueError(
        "Необходимо указать XMLRIVER_USER_ID и XMLRIVER_API_KEY в .env файле"
    ) 