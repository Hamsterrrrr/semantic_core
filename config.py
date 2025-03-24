import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Конфигурация API ключей
XMLRIVER_USER_ID = os.getenv("XMLRIVER_USER_ID")
XMLRIVER_API_KEY = os.getenv("XMLRIVER_API_KEY")

# Проверка наличия необходимых переменных
if not all([XMLRIVER_USER_ID, XMLRIVER_API_KEY]):
    raise ValueError(
        "Необходимо указать XMLRIVER_USER_ID и XMLRIVER_API_KEY в .env файле"
    ) 