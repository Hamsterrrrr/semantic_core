import requests

# Токен доступа
access_token = "y0__wgBEInk4-AHGJLLNCCh0-yKEhZ-qTuIM6sDjt1IVfy4ewTQwBkk"

# URL для создания отчета
url = "https://api.direct.yandex.com/json/v5/reports"

# Заголовки запроса
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept-Language": "ru",
    "Content-Type": "application/json; charset=utf-8"  # Явно указываем кодировку
}

# Тело запроса
payload = {
    "method": "CreateNewWordstatReport",
    "params": {
        "Phrases": ["синтепон"]
    }
}

# Отправка запроса
try:
    response = requests.post(url, headers=headers, json=payload)
    response.encoding = "utf-8"  # Принудительно задаем кодировку ответа
    
    if response.status_code == 200:
        report_id = response.json()["data"]
        print("Идентификатор отчета:", report_id)
    else:
        print(f"Ошибка {response.status_code}. Ответ сервера:")
        print(response.text)  # Текст уже декодирован в utf-8

except Exception as e:
    print(f"Произошла ошибка: {str(e)}")