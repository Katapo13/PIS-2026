"""
Infrastructure Layer: RequestController (FastAPI)

Входящий адаптер для REST API.
Использует CreateRequestUseCase (входящий порт).
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from application.port.in import CreateRequestUseCase, CreateRequestCommand


# DTO для REST API
class CreateRequestDto(BaseModel):
    """DTO: Запрос на создание заявки"""
    coordinator_id: str
    zone: str
    volunteer_ids: List[str]


class CreateRequestResponseDto(BaseModel):
    """DTO: Ответ после создания заявки"""
    request_id: str


class RequestController:
    """
    Адаптер: REST API контроллер (FastAPI)
    
    Входящий адаптер, который вызывает систему через
    CreateRequestUseCase (входящий порт)
    """
    
    def __init__(self, app: FastAPI, use_case: CreateRequestUseCase):
        """
        Инициализация контроллера
        
        Args:
            app: FastAPI приложение
            use_case: Use-case создания заявки (входящий порт)
        """
        self._use_case = use_case
        
        # Регистрация маршрутов
        @app.post("/api/requests", response_model=CreateRequestResponseDto)
        async def create_request(dto: CreateRequestDto):
            """
            POST /api/requests - Создать заявку
            
            Body:
            {
              "coordinator_id": "coordinator-001",
              "zone": "NORTH",
              "volunteer_ids": ["vol-123", "vol-456", "vol-789"]
            }
            
            Response:
            {
              "request_id": "REQ-2024-0042"
            }
            """
            try:
                # Преобразовать DTO → Command
                command = CreateRequestCommand(
                    coordinator_id=dto.coordinator_id,
                    zone=dto.zone,
                    volunteer_ids=dto.volunteer_ids
                )
                
                # Вызвать use-case (входящий порт)
                request_id = self._use_case.create_request(command)
                
                return CreateRequestResponseDto(request_id=request_id)
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.get("/api/health")
        async def health_check():
            """GET /api/health - Health check"""
            return {"status": "OK", "service": "Request Service (ПСО Юго-Запад)"}
