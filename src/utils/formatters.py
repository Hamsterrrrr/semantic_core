"""
Утилиты для форматирования данных
"""
import pandas as pd
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def format_number(number: Any) -> str:
    """
    Форматирует число с разделителями тысяч
    
    Args:
        number: Число для форматирования
        
    Returns:
        Отформатированная строка
    """
    try:
        if isinstance(number, str) and number.isdigit():
            return "{:,}".format(int(number)).replace(",", " ")
        elif isinstance(number, (int, float)):
            return "{:,}".format(int(number)).replace(",", " ")
        else:
            return str(number)
    except Exception:
        return str(number)

def save_to_csv(data: Dict[str, List[Dict]], filename: str) -> bool:
    """
    Сохраняет данные в CSV-файл
    
    Args:
        data: Данные для сохранения
        filename: Имя файла
        
    Returns:
        True в случае успеха, False в случае ошибки
    """
    try:
        # Создаем DataFrame для основной таблицы
        rows = []
        categories = list(data.keys())
        
        # Определяем максимальное количество запросов в категории
        max_phrases = max(len(phrases) for phrases in data.values()) if data else 0
        
        # Подготавливаем данные для таблицы
        for i in range(max_phrases):
            row = {}
            for category in categories:
                phrases = data[category]
                if i < len(phrases):
                    phrase = phrases[i]
                    if isinstance(phrase, dict) and "phrase" in phrase and "number" in phrase:
                        # Форматируем строку с фразой и показами
                        row[category] = f"{phrase['phrase']} ({format_number(phrase['number'])})"
                    else:
                        row[category] = phrase if isinstance(phrase, str) else str(phrase)
                else:
                    row[category] = ""
            rows.append(row)
        
        # Создаем DataFrame и сохраняем в CSV
        df = pd.DataFrame(rows)
        
        # Добавляем заголовок с информацией
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Семантическое ядро\n")
            f.write(f"# Дата создания: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write(f"# Категории: {', '.join(categories)}\n")
            f.write(f"# Всего запросов: {sum(len(phrases) for phrases in data.values())}\n\n")
        
        # Сохраняем DataFrame в CSV с добавлением к существующему файлу
        df.to_csv(filename, index=False, encoding='utf-8', mode='a')
        
        # Пробуем создать Excel-файл, если установлена библиотека openpyxl
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            from openpyxl.utils import get_column_letter
            
            excel_filename = filename.replace('.csv', '.xlsx')
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Семантическое ядро')
                
                # Получаем рабочий лист для форматирования
                worksheet = writer.sheets['Семантическое ядро']
                
                # Форматируем заголовки
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = worksheet.cell(row=1, column=col_num)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
                    
                    # Автоподбор ширины столбцов
                    worksheet.column_dimensions[get_column_letter(col_num)].width = max(
                        len(column_title) + 2,
                        max(len(str(df.iloc[i, col_num-1])) for i in range(len(df))) + 2
                    )
            
            logger.info(f"Результаты успешно сохранены в '{filename}' и '{excel_filename}'")
        except ImportError:
            logger.warning("Библиотека openpyxl не установлена. Excel-файл не создан.")
            logger.info(f"Для создания Excel-файла установите библиотеку: pip install openpyxl")
            logger.info(f"Результаты сохранены только в '{filename}'")
        
        # Также сохраняем в JSON для отладки
        with open(filename.replace('.csv', '.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении результатов: {str(e)}")
        return False 