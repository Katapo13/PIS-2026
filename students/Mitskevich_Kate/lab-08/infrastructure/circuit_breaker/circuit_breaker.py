from circuitbreaker import circuit_breaker
import httpx
from typing import Optional


class CircuitBreakerConfig:
    """Конфигурация Circuit Breaker для сервисов"""
    
    @staticmethod
    @circuit_breaker(
        failure_threshold=5,      # 5 ошибок для открытия
        recovery_timeout=30,      # 30 секунд до попытки восстановления
        expected_exception=httpx.HTTPStatusError,
        name="category_service_cb"
    )
    async def call_category_service(endpoint: str, method: str = "GET") -> Optional[dict]:
        """Вызов Category Service с защитой Circuit Breaker"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.request(
                method,
                f"http://category-service:8002{endpoint}"
            )
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    @circuit_breaker(
        failure_threshold=3,
        recovery_timeout=60,
        expected_exception=httpx.HTTPStatusError,
        name="report_service_cb"
    )
    async def call_report_service(endpoint: str) -> Optional[dict]:
        """Вызов Report Service с защитой Circuit Breaker"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"http://report-service:8003{endpoint}")
            response.raise_for_status()
            return response.json()


# Использование в Transaction Service
async def get_category_with_fallback(category_id: str):
    try:
        return await CircuitBreakerConfig.call_category_service(f"/api/categories/{category_id}")
    except Exception as e:
        # Fallback: возвращаем кэшированные данные
        print(f"Circuit breaker open, using fallback: {e}")
        return await get_category_from_cache(category_id)