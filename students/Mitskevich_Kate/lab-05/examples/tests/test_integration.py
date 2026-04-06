import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from infrastructure.adapter.out.models import Base, TransactionModel
from infrastructure.config.database import get_session


# Настройка тестовой БД
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/test_money_db"


@pytest.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(test_session):
    async def override_get_session():
        yield test_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


class TestTransactionIntegration:
    """Интеграционные тесты транзакций"""
    
    async def test_create_income_via_api(self, client, test_session):
        """Тест: создание дохода через API"""
        response = await client.post(
            "/api/transactions/income",
            json={
                "user_id": "user-001",
                "amount": 1000.0,
                "description": "Зарплата",
                "idempotency_key": "int-test-001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data
        assert data["status"] == "success"
        
        # Проверка записи в БД
        result = await test_session.execute(
            select(TransactionModel).where(
                TransactionModel.idempotency_key == "int-test-001"
            )
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.amount == 1000.0
    
    async def test_get_transaction_by_id(self, client, test_session):
        """Тест: получение транзакции по ID"""
        # Сначала создаём транзакцию
        create_response = await client.post(
            "/api/transactions/income",
            json={
                "user_id": "user-001",
                "amount": 500.0,
                "idempotency_key": "int-test-002"
            }
        )
        tx_id = create_response.json()["transaction_id"]
        
        # Получаем её через API
        get_response = await client.get(f"/api/transactions/{tx_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["transaction_id"] == tx_id
        assert data["amount"] == 500.0
        assert data["type"] == "INCOME"
    
    async def test_idempotency(self, client, test_session):
        """Тест: идемпотентность - повторный запрос с тем же ключом"""
        request_data = {
            "user_id": "user-001",
            "amount": 300.0,
            "idempotency_key": "int-test-003"
        }
        
        # Первый запрос
        response1 = await client.post("/api/transactions/income", json=request_data)
        tx_id1 = response1.json()["transaction_id"]
        
        # Второй запрос с тем же ключом
        response2 = await client.post("/api/transactions/income", json=request_data)
        tx_id2 = response2.json()["transaction_id"]
        
        assert tx_id1 == tx_id2
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    async def test_list_transactions(self, client, test_session):
        """Тест: список транзакций пользователя"""
        # Создаём несколько транзакций
        for i in range(3):
            await client.post(
                "/api/transactions/income",
                json={
                    "user_id": "user-list",
                    "amount": 100.0 * (i + 1),
                    "idempotency_key": f"list-test-{i}"
                }
            )
        
        # Получаем список
        response = await client.get(
            "/api/transactions/",
            params={"user_id": "user-list", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    async def test_not_found(self, client):
        """Тест: транзакция не найдена"""
        response = await client.get("/api/transactions/TXN-9999-99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Transaction not found"