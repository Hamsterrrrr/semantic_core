import pandas as pd
import xml.etree.ElementTree as ET
import json
import os
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
import csv
import yaml

logger = logging.getLogger(__name__)

class FeedGenerator:
    """Класс для генерации фидов в различных форматах"""
    
    SUPPORTED_FORMATS = ["xml", "csv", "json", "yml"]
    
    # Добавляем определение специфичных атрибутов для разных категорий
    CATEGORY_ATTRIBUTES = {
        "clothing": ["size", "color", "gender", "material", "season", "pattern"],
        "electronics": ["cpu", "ram", "storage", "screen_size", "warranty", "weight", "dimensions"],
        "food": ["expiration_date", "ingredients", "nutrition_facts", "weight", "storage_conditions"],
        "books": ["author", "isbn", "publisher", "language", "pages", "publication_date"],
        "furniture": ["width", "height", "depth", "weight", "material", "style", "assembly_required"]
    }
    
    def __init__(self, data: Union[pd.DataFrame, List[Dict]], output_dir: Path, category_type: str = None):
        """
        Инициализация генератора фидов
        
        Args:
            data: Данные для генерации фида (DataFrame или список словарей)
            output_dir: Директория для сохранения фидов
            category_type: Тип категории товаров (clothing, electronics, food, books, furniture)
        """
        self.output_dir = output_dir
        self.category_type = category_type
        
        # Преобразуем данные в DataFrame если они переданы как список словарей
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            self.data = data
            
        # Создаем директорию для сохранения фидов, если она не существует
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        self.logger = logging.getLogger(__name__)
        
    def generate_all_feeds(self, base_filename: str) -> Dict[str, str]:
        """
        Генерирует фиды во всех поддерживаемых форматах
        
        Args:
            base_filename: Базовое имя файла
            
        Returns:
            Словарь с путями к сгенерированным файлам
        """
        result_files = {}
        
        for format_type in self.SUPPORTED_FORMATS:
            try:
                # Добавляем категорию в имя файла, если она указана
                if self.category_type:
                    filename = f"{base_filename}_{self.category_type}.{format_type}"
                else:
                    filename = f"{base_filename}.{format_type}"
                    
                file_path = self.output_dir / filename
                
                if format_type == "xml":
                    self._generate_xml_feed(file_path)
                elif format_type == "csv":
                    self._generate_csv_feed(file_path)
                elif format_type == "json":
                    self._generate_json_feed(file_path)
                elif format_type == "yml":
                    self._generate_yml_feed(file_path)
                    
                result_files[format_type] = str(file_path)
                self.logger.info(f"Сгенерирован фид в формате {format_type}: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Ошибка при генерации фида в формате {format_type}: {str(e)}")
        
        # Генерируем специализированный фид в зависимости от категории
        if self.category_type:
            try:
                specialized_format = self._get_specialized_format()
                if specialized_format:
                    filename = f"{base_filename}_{self.category_type}_specialized.{specialized_format}"
                    file_path = self.output_dir / filename
                    
                    self._generate_specialized_feed(file_path)
                    result_files["specialized"] = str(file_path)
                    self.logger.info(f"Сгенерирован специализированный фид для {self.category_type}: {file_path}")
            except Exception as e:
                self.logger.error(f"Ошибка при генерации специализированного фида: {str(e)}")
        
        return result_files
    
    def _get_specialized_format(self) -> str:
        """Определяет подходящий формат для специализированного фида в зависимости от категории"""
        # Для каждой категории можно определить свой оптимальный формат
        category_formats = {
            "clothing": "xml",      # XML лучше подходит для передачи атрибутов одежды
            "electronics": "json",  # JSON подходит для сложных технических характеристик
            "food": "csv",          # CSV прост в использовании для продуктов питания
            "books": "xml",         # XML подходит для структурированных данных о книгах
            "furniture": "json"     # JSON для мебели с множеством параметров
        }
        
        return category_formats.get(self.category_type)
    
    def _generate_specialized_feed(self, file_path: Path) -> None:
        """
        Генерирует специализированный фид для конкретной категории
        
        Args:
            file_path: Путь для сохранения файла
        """
        # Получаем расширение файла
        extension = file_path.suffix.lstrip(".")
        
        if extension == "xml":
            self._generate_specialized_xml(file_path)
        elif extension == "json":
            self._generate_specialized_json(file_path)
        elif extension == "csv":
            self._generate_specialized_csv(file_path)
    
    def _generate_specialized_xml(self, file_path: Path) -> None:
        """Генерирует специализированный XML-фид с атрибутами для конкретной категории"""
        root = ET.Element("feed")
        root.set("category_type", self.category_type)
        
        # Добавляем метаданные
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "generated_at").text = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(metadata, "items_count").text = str(len(self.data))
        ET.SubElement(metadata, "category_type").text = self.category_type
        
        # Получаем список специфичных атрибутов для категории
        category_attributes = self.CATEGORY_ATTRIBUTES.get(self.category_type, [])
        
        # Добавляем товары
        items = ET.SubElement(root, "items")
        
        for _, row in self.data.iterrows():
            item = ET.SubElement(items, "item")
            
            # Добавляем основные поля
            for column in self.data.columns:
                if pd.notna(row[column]):
                    # Пропускаем специфичные атрибуты, они будут добавлены отдельно
                    if column not in category_attributes:
                        ET.SubElement(item, column).text = str(row[column])
            
            # Добавляем специфичные атрибуты в отдельном блоке
            attributes = ET.SubElement(item, "attributes")
            for attr in category_attributes:
                if attr in self.data.columns and pd.notna(row[attr]):
                    ET.SubElement(attributes, attr).text = str(row[attr])
        
        # Создаем XML-дерево и сохраняем в файл
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)
    
    def _generate_specialized_json(self, file_path: Path) -> None:
        """Генерирует специализированный JSON-фид с атрибутами для конкретной категории"""
        # Получаем список специфичных атрибутов для категории
        category_attributes = self.CATEGORY_ATTRIBUTES.get(self.category_type, [])
        
        # Создаем структуру для фида
        specialized_data = {
            "metadata": {
                "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "items_count": len(self.data),
                "category_type": self.category_type
            },
            "items": []
        }
        
        # Добавляем каждый товар
        for _, row in self.data.iterrows():
            item = {}
            attributes = {}
            
            # Обрабатываем все колонки
            for column in self.data.columns:
                if pd.notna(row[column]):
                    # Специфичные атрибуты добавляем в отдельный блок
                    if column in category_attributes:
                        attributes[column] = row[column]
                    else:
                        item[column] = row[column]
            
            # Добавляем блок с атрибутами
            item["attributes"] = attributes
            specialized_data["items"].append(item)
        
        # Записываем в файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(specialized_data, f, ensure_ascii=False, indent=2)
    
    def _generate_specialized_csv(self, file_path: Path) -> None:
        """Генерирует специализированный CSV-фид с атрибутами для конкретной категории"""
        # Для CSV просто добавляем все поля в одну таблицу
        self.data.to_csv(file_path, index=False, encoding="utf-8")
        
        # Добавляем информацию о типе категории в отдельный файл metadata
        metadata_file = file_path.with_name(f"{file_path.stem}_metadata.json")
        metadata = {
            "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items_count": len(self.data),
            "category_type": self.category_type,
            "category_attributes": self.CATEGORY_ATTRIBUTES.get(self.category_type, [])
        }
        
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _generate_xml_feed(self, file_path: Path) -> None:
        """
        Генерирует XML-фид
        
        Args:
            file_path: Путь для сохранения файла
        """
        root = ET.Element("feed")
        
        # Добавляем метаданные
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "generated_at").text = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(metadata, "items_count").text = str(len(self.data))
        
        # Добавляем товары
        items = ET.SubElement(root, "items")
        
        for _, row in self.data.iterrows():
            item = ET.SubElement(items, "item")
            
            # Добавляем все поля из DataFrame
            for column in self.data.columns:
                # Пропускаем пустые значения
                if pd.notna(row[column]):
                    # Преобразуем все значения в строки
                    value = str(row[column])
                    
                    # Создаем элемент с именем колонки и значением
                    ET.SubElement(item, column).text = value
        
        # Создаем XML-дерево и сохраняем в файл
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)
    
    def _generate_csv_feed(self, file_path: Path) -> None:
        """
        Генерирует CSV-фид
        
        Args:
            file_path: Путь для сохранения файла
        """
        self.data.to_csv(file_path, index=False, encoding="utf-8")
    
    def _generate_json_feed(self, file_path: Path) -> None:
        """
        Генерирует JSON-фид
        
        Args:
            file_path: Путь для сохранения файла
        """
        # Создаем структуру JSON-фида
        feed_data = {
            "metadata": {
                "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "items_count": len(self.data)
            },
            "items": self.data.to_dict(orient="records")
        }
        
        # Записываем в файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feed_data, f, ensure_ascii=False, indent=2)
    
    def _generate_yml_feed(self, file_path: Path) -> None:
        """
        Генерирует YML-фид (Яндекс.Маркет)
        
        Args:
            file_path: Путь для сохранения файла
        """
        # Создаем корневой элемент
        root = ET.Element("yml_catalog", date=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
        shop = ET.SubElement(root, "shop")
        
        # Добавляем блок с товарами
        offers = ET.SubElement(shop, "offers")
        
        # Добавляем каждый товар
        for idx, row in self.data.iterrows():
            offer = ET.SubElement(offers, "offer", id=str(idx + 1))
            
            # Добавляем все поля из DataFrame
            for column in self.data.columns:
                # Пропускаем пустые значения
                if pd.notna(row[column]):
                    # Для Яндекс.Маркета некоторые поля должны быть атрибутами, 
                    # а не элементами, но для упрощения делаем все элементами
                    ET.SubElement(offer, column).text = str(row[column])
        
        # Создаем XML-дерево и сохраняем в файл
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)

    @classmethod
    def from_csv(cls, csv_file_path: str, output_dir: Path, category_type: str = None) -> 'FeedGenerator':
        """
        Создает генератор фидов из CSV-файла
        
        Args:
            csv_file_path: Путь к CSV-файлу
            output_dir: Директория для сохранения фидов
            category_type: Тип категории товаров
            
        Returns:
            Экземпляр FeedGenerator
        """
        df = pd.read_csv(csv_file_path)
        return cls(df, output_dir, category_type)
    
    @classmethod
    def from_excel(cls, excel_file_path: str, output_dir: Path, category_type: str = None) -> 'FeedGenerator':
        """
        Создает генератор фидов из Excel-файла
        
        Args:
            excel_file_path: Путь к Excel-файлу
            output_dir: Директория для сохранения фидов
            category_type: Тип категории товаров
            
        Returns:
            Экземпляр FeedGenerator
        """
        df = pd.read_excel(excel_file_path)
        return cls(df, output_dir, category_type) 