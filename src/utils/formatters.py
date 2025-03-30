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
        filename: Имя файла без расширения
        
    Returns:
        True в случае успеха, False в случае ошибки
    """
    try:
        # Добавляем расширение .csv
        csv_filename = f"{filename}.csv"
        
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
        with open(csv_filename, 'w', encoding='utf-8') as f:
            f.write("# Семантическое ядро\n")
            f.write(f"# Дата создания: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write(f"# Категории: {', '.join(categories)}\n")
            f.write(f"# Всего запросов: {sum(len(phrases) for phrases in data.values())}\n\n")
        
        # Сохраняем DataFrame в CSV с добавлением к существующему файлу
        df.to_csv(csv_filename, index=False, encoding='utf-8', mode='a')
        
        # Также сохраняем в JSON для отладки
        json_filename = f"{filename}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Результаты успешно сохранены в '{csv_filename}'")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении результатов: {str(e)}")
        return False

def save_to_advanced_formats(data: Dict[str, List[Dict]], base_filename: str) -> None:
    """Сохраняет результаты в различных форматах с расширенной информацией"""
    try:
        # Создание Excel с несколькими листами
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            excel_filename = f"{base_filename}.xlsx"
            
            # Удаляем стандартный лист
            wb = openpyxl.Workbook()
            ws_default = wb.active
            wb.remove(ws_default)
            
            # Общая статистика
            ws_stats = wb.create_sheet("Статистика")
            ws_stats['A1'] = "Семантическое ядро - Статистика"
            ws_stats['A1'].font = Font(bold=True, size=14)
            
            ws_stats['A3'] = "Категория"
            ws_stats['B3'] = "Количество фраз"
            ws_stats['C3'] = "Среднее количество показов"
            ws_stats['D3'] = "Максимальное количество показов"
            
            row = 4
            for category, phrases in data.items():
                shows = [int(p.get("number", 0)) for p in phrases]
                avg_shows = sum(shows) / len(shows) if shows else 0
                max_shows = max(shows) if shows else 0
                
                ws_stats[f'A{row}'] = category
                ws_stats[f'B{row}'] = len(phrases)
                ws_stats[f'C{row}'] = int(avg_shows)
                ws_stats[f'D{row}'] = max_shows
                row += 1
            
            # Форматирование статистики
            for col in ['A', 'B', 'C', 'D']:
                ws_stats[f'{col}3'].font = Font(bold=True)
                ws_stats[f'{col}3'].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
            
            # Основной лист с данными
            ws_main = wb.create_sheet("Семантическое ядро")
            
            # Заголовки
            ws_main['A1'] = "Категория"
            ws_main['B1'] = "Фраза"
            ws_main['C1'] = "Показы"
            ws_main['D1'] = "Релевантность"
            ws_main['E1'] = "Конкурентность"
            
            # Применяем форматирование к заголовкам
            for col in ['A', 'B', 'C', 'D', 'E']:
                ws_main[f'{col}1'].font = Font(bold=True)
                ws_main[f'{col}1'].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
            
            # Заполняем данными
            row = 2
            for category, phrases in data.items():
                for phrase in phrases:
                    ws_main[f'A{row}'] = category
                    ws_main[f'B{row}'] = phrase.get("phrase", "")
                    ws_main[f'C{row}'] = phrase.get("number", 0)
                    ws_main[f'D{row}'] = phrase.get("relevance", 0)
                    ws_main[f'E{row}'] = phrase.get("конкурентность", "")
                    row += 1
            
            # Автоподбор ширины столбцов
            for col in ['A', 'B', 'C', 'D', 'E']:
                column_width = max(len(str(ws_main[f'{col}{row}'].value)) for row in range(1, len(data) + 2)) + 2
                ws_main.column_dimensions[col].width = column_width
            
            # Создаем отдельные листы для каждой категории
            for category, phrases in data.items():
                # Ограничение на длину имени листа в Excel (31 символ)
                sheet_name = category[:31].replace('/', '_')
                ws_category = wb.create_sheet(sheet_name)
                
                # Заголовки
                ws_category['A1'] = "Фраза"
                ws_category['B1'] = "Показы"
                ws_category['C1'] = "Релевантность"
                
                # Форматирование заголовков
                for col in ['A', 'B', 'C']:
                    ws_category[f'{col}1'].font = Font(bold=True)
                    ws_category[f'{col}1'].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
                
                # Заполняем данными
                for i, phrase in enumerate(phrases, 2):
                    ws_category[f'A{i}'] = phrase.get("phrase", "")
                    ws_category[f'B{i}'] = phrase.get("number", 0)
                    ws_category[f'C{i}'] = phrase.get("relevance", 0)
                
                # Автоподбор ширины столбцов
                for col in ['A', 'B', 'C']:
                    max_length = max(len(str(ws_category[f'{col}{row}'].value)) for row in range(1, len(phrases) + 2))
                    ws_category.column_dimensions[col].width = max_length + 2
            
            # Сохраняем Excel-файл
            wb.save(excel_filename)
            logger.info(f"Создан расширенный Excel-файл: {excel_filename}")
            
        except ImportError:
            logger.warning("Библиотека openpyxl не установлена. Excel-файл не создан.")
        
        # Создание отчета в HTML формате
        html_filename = f"{base_filename}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Семантическое ядро</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                    th { background-color: #f2f2f2; text-align: left; padding: 8px; }
                    td { border: 1px solid #ddd; padding: 8px; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .category { margin-top: 30px; }
                    .high { color: green; }
                    .medium { color: orange; }
                    .low { color: red; }
                </style>
            </head>
            <body>
                <h1>Отчет по семантическому ядру</h1>
                <p>Дата создания: """ + pd.Timestamp.now().strftime('%d.%m.%Y %H:%M') + """</p>
            """)
            
            # Общая статистика
            f.write("""
                <h2>Общая статистика</h2>
                <table>
                    <tr>
                        <th>Категория</th>
                        <th>Количество фраз</th>
                        <th>Среднее количество показов</th>
                    </tr>
            """)
            
            for category, phrases in data.items():
                shows = [int(p.get("number", 0)) for p in phrases]
                avg_shows = int(sum(shows) / len(shows)) if shows else 0
                
                f.write(f"""
                    <tr>
                        <td>{category}</td>
                        <td>{len(phrases)}</td>
                        <td>{avg_shows}</td>
                    </tr>
                """)
            
            f.write("</table>")
            
            # Таблицы для каждой категории
            for category, phrases in data.items():
                f.write(f"""
                    <div class="category">
                        <h2>Категория: {category}</h2>
                        <table>
                            <tr>
                                <th>Фраза</th>
                                <th>Показы</th>
                            </tr>
                """)
                
                # Сортировка фраз по показам
                sorted_phrases = sorted(phrases, key=lambda x: int(x.get("number", 0)), reverse=True)
                
                for phrase in sorted_phrases:
                    phrase_text = phrase.get("phrase", "")
                    shows = phrase.get("number", 0)
                    
                    # Определение класса для показов
                    show_class = "high" if int(shows) > 5000 else "medium" if int(shows) > 1000 else "low"
                    
                    f.write(f"""
                        <tr>
                            <td>{phrase_text}</td>
                            <td class="{show_class}">{shows}</td>
                        </tr>
                    """)
                
                f.write("""
                        </table>
                    </div>
                """)
            
            f.write("""
            </body>
            </html>
            """)
            
            logger.info(f"Создан HTML-отчет: {html_filename}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении результатов в расширенных форматах: {str(e)}")
        return False 