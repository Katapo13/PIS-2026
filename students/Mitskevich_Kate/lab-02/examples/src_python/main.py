"""
Main Application: FastAPI Entry Point

Точка входа для REST API приложения (FastAPI).
"""
from fastapi import FastAPI
import uvicorn

from infrastructure.config import get_container


def create_app() -> FastAPI:
    """
    Создать и настроить FastAPI приложение
    
    Returns:
        Настроенное FastAPI приложение
    """
    app = FastAPI(
        title="Request Service (ПСО Юго-Запад)",
        description="Сервис управления заявками на поисково-спасательные операции",
        version="1.0.0"
    )
    
    # Получить DI-контейнер и настроить приложение
    container = get_container()
    container.configure_web_app(app)
    
    return app


# Создать приложение
app = create_app()


if __name__ == "__main__":
    # Запустить сервер
    print("🚀 Запуск Request Service...")
    print("📖 Документация API: http://localhost:8000/docs")
    print()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
