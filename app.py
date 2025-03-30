import asyncio
import os
import logging
import uvicorn
import uuid
import pandas as pd
from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime
import shutil
import tempfile

from config import XMLRIVER_USER_ID, XMLRIVER_API_KEY, XMLRIVER_BASE_URL
from semantic_core import SemanticModel
from src.ai.gpt_client import GPTProcessor
from src.api.xmlriver_api import XmlRiverApi
from src.feeds.feed_generator import FeedGenerator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Создаем директории для результатов
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
FEEDS_DIR = Path("feeds")
FEEDS_DIR.mkdir(exist_ok=True)

# Инициализация FastAPI
app = FastAPI(title="Генератор семантического ядра и фидов")

# Подключаем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Словари для хранения статуса задач
seo_tasks_status = {}
feed_tasks_status = {}

async def process_url_task(task_id: str, url: str):
    """Фоновая задача для обработки URL"""
    try:
        seo_tasks_status[task_id] = {"status": "in_progress", "message": "Задача запущена"}
        
        # Инициализация API клиентов
        xmlriver_api = XmlRiverApi(
            user_id=XMLRIVER_USER_ID,
            api_key=XMLRIVER_API_KEY,
            base_url=XMLRIVER_BASE_URL
        )
        gpt_processor = GPTProcessor()
        semantic_model = SemanticModel(xmlriver_api, gpt_processor)

        # Создаем директорию для результатов задачи
        task_dir = RESULTS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Обновляем статус
        seo_tasks_status[task_id] = {"status": "processing", "message": "Обработка URL..."}
        
        # Обработка URL
        results = await semantic_model.process_url(url)
        
        if not results:
            seo_tasks_status[task_id] = {"status": "error", "message": "Не удалось получить результаты"}
            return
        
        # Сохранение результатов
        file_base_path = task_dir / "semantic_core"
        await semantic_model.save_results(results, str(file_base_path))
        
        # Обновляем статус, добавляя ссылки на файлы
        seo_tasks_status[task_id] = {
            "status": "completed",
            "message": "Обработка завершена успешно",
            "files": {
                "csv": f"/results/{task_id}/semantic_core.csv",
                "xlsx": f"/results/{task_id}/semantic_core.xlsx",
                "html": f"/results/{task_id}/semantic_core.html",
                "json": f"/results/{task_id}/semantic_core.json"
            },
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обработке URL: {str(e)}")
        seo_tasks_status[task_id] = {"status": "error", "message": f"Ошибка: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "seo_tasks": seo_tasks_status,
            "feed_tasks": feed_tasks_status
        }
    )

@app.post("/submit")
async def submit_url(background_tasks: BackgroundTasks, url: str = Form(...)):
    """Отправка URL для обработки"""
    # Создаем уникальный ID для задачи
    task_id = str(uuid.uuid4())
    
    # Запускаем обработку URL в фоновом режиме
    background_tasks.add_task(process_url_task, task_id, url)
    
    # Инициализируем статус задачи
    seo_tasks_status[task_id] = {"status": "pending", "message": "Задача в очереди"}
    
    # Перенаправляем на страницу статуса
    return RedirectResponse(url=f"/task/{task_id}", status_code=303)

@app.get("/task/{task_id}", response_class=HTMLResponse)
async def task_status(request: Request, task_id: str):
    """Страница со статусом задачи"""
    # Проверяем в обоих словарях статусов
    task_info = seo_tasks_status.get(task_id)
    task_type = "seo"
    
    if not task_info:
        task_info = feed_tasks_status.get(task_id)
        task_type = "feed"
    
    if not task_info:
        task_info = {"status": "not_found", "message": "Задача не найдена"}
        task_type = "unknown"
    
    return templates.TemplateResponse(
        "task.html", 
        {
            "request": request, 
            "task_id": task_id, 
            "task_info": task_info,
            "task_type": task_type
        }
    )

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """API для получения статуса задачи"""
    # Проверяем в обоих словарях статусов
    if task_id in seo_tasks_status:
        return {"type": "seo", "data": seo_tasks_status[task_id]}
    elif task_id in feed_tasks_status:
        return {"type": "feed", "data": feed_tasks_status[task_id]}
    else:
        return {"status": "not_found", "message": "Задача не найдена"}

@app.get("/results/{task_id}/{filename}")
async def get_result_file(task_id: str, filename: str):
    """Получение файла с результатами"""
    file_path = RESULTS_DIR / task_id / filename
    if not file_path.exists():
        return {"error": "Файл не найден"}
    
    # Определяем MIME-тип по расширению
    mime_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
        "json": "application/json"
    }
    
    # Получаем расширение файла
    extension = filename.split(".")[-1]
    media_type = mime_types.get(extension, "application/octet-stream")
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type=media_type
    )

# Новые маршруты для работы с фидами
@app.get("/feeds", response_class=HTMLResponse)
async def feeds_page(request: Request):
    """Страница для создания фидов"""
    return templates.TemplateResponse(
        "feeds.html", 
        {"request": request, "feed_tasks": feed_tasks_status}
    )

async def process_feed_task(task_id: str, file_path: str, file_format: str, category_type: str = None):
    """Фоновая задача для обработки фида"""
    try:
        feed_tasks_status[task_id] = {"status": "in_progress", "message": "Задача запущена", "category_type": category_type}
        
        # Создаем директорию для результатов задачи
        task_dir = FEEDS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Обновляем статус
        feed_tasks_status[task_id] = {"status": "processing", "message": "Обработка файла...", "category_type": category_type}
        
        # Определяем тип файла и загружаем данные
        if file_format == "csv":
            feed_generator = FeedGenerator.from_csv(file_path, task_dir, category_type)
        elif file_format in ["xlsx", "xls"]:
            feed_generator = FeedGenerator.from_excel(file_path, task_dir, category_type)
        else:
            feed_tasks_status[task_id] = {
                "status": "error", 
                "message": f"Неподдерживаемый формат файла: {file_format}",
                "category_type": category_type
            }
            return
        
        # Генерируем фиды во всех поддерживаемых форматах
        feed_tasks_status[task_id] = {"status": "generating", "message": "Генерация фидов...", "category_type": category_type}
        result_files = feed_generator.generate_all_feeds(f"product_feed")
        
        # Формируем файловые пути для веб-интерфейса
        web_paths = {}
        for format_type, file_path in result_files.items():
            filename = os.path.basename(file_path)
            web_paths[format_type] = f"/feeds/{task_id}/{filename}"
        
        # Обновляем статус, добавляя ссылки на файлы
        feed_tasks_status[task_id] = {
            "status": "completed",
            "message": "Фиды успешно сгенерированы",
            "files": web_paths,
            "category_type": category_type,
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фида: {str(e)}")
        feed_tasks_status[task_id] = {"status": "error", "message": f"Ошибка: {str(e)}", "category_type": category_type}

@app.post("/submit-feed")
async def submit_feed(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    category_type: str = Form(None)
):
    """Загрузка файла для создания фида"""
    try:
        # Создаем уникальный ID для задачи
        task_id = str(uuid.uuid4())
        
        # Сохраняем временный файл
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        # Определяем формат файла
        file_format = suffix.lstrip('.')
        
        # Запускаем обработку файла в фоновом режиме
        background_tasks.add_task(process_feed_task, task_id, temp_file_path, file_format, category_type)
        
        # Инициализируем статус задачи
        feed_tasks_status[task_id] = {
            "status": "pending", 
            "message": "Задача в очереди",
            "category_type": category_type
        }
        
        # Перенаправляем на страницу статуса
        return RedirectResponse(url=f"/task/{task_id}", status_code=303)
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")

@app.get("/feeds/{task_id}/{filename}")
async def get_feed_file(task_id: str, filename: str):
    """Получение файла с фидом"""
    file_path = FEEDS_DIR / task_id / filename
    if not file_path.exists():
        return {"error": "Файл не найден"}
    
    # Определяем MIME-тип по расширению
    mime_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "xml": "application/xml",
        "yml": "application/xml"
    }
    
    # Получаем расширение файла
    extension = filename.split(".")[-1]
    media_type = mime_types.get(extension, "application/octet-stream")
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type=media_type
    )

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)