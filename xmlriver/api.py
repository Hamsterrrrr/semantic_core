import aiohttp
import json

class XmlRiverApi:
    def __init__(self, user_id: str, api_key: str, endpoint: str = "http://xmlriver.com/wordstat/json"):
        self.user_id = user_id
        self.api_key = api_key
        self.endpoint = endpoint

    async def get_data(self, query: str, region: str = "ru", results_count: int = 10) -> dict:
        params = {
            "user": self.user_id,
            "key": self.api_key,
            "query": query,
            "region": region,
            "count": results_count
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoint, params=params) as response:
                    response.raise_for_status()
                    return await response.json()  # Возвращаем JSON-ответ
        except aiohttp.ClientError as e:
            print(f"Ошибка запроса: {e}")
            return {}
        except ValueError:
            print("Ошибка обработки JSON ответа")
            return {}

    @staticmethod
    def write_json(data: dict, filename: str = "results.json"):
        with open(filename, "w", encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)