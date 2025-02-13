
import re

def refine_output(raw_output: list) -> list:
    if not raw_output:
        return []
    
    # Временно просто разделим по запятым без дополнительной логики:
    return [item.strip() for item in raw_output if item.strip()]

def validate_phrases(phrases: list, text: str) -> list:
    """
    Простейшая функция валидации фраз.
    Здесь можно добавить дополнительную проверку, например,
    чтобы фраза содержала хотя бы одно слово из исходного текста или удовлетворяла другим условиям.
    Для примера вернем те фразы, длина которых больше 3 символов.
    """
    return [phrase.strip() for phrase in phrases if len(phrase.strip()) > 3]
