import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from infrastructure.config.database import get_async_session
from infrastructure.adapter.out.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer


class TestTransactionE2E:
    
    @pytest.fixture(scope="class")
    def postgres_container(self):
        with PostgresContainer("postgres:15-alpine") as container:
            yield container
    
    @pytest.fixture
    async def db_session(self, postgres_container):
        database_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    @pytest.fixture
    def client(self, db_session):
        async def override_get_session():
            yield db_session
        
        app.dependency_overrides[get_async_session] = override_get_session
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_full_transaction_flow(self, client, db_session):
        """
        E2E сценарий:
        1. Создать категории (через БД напрямую для теста)
        2. Создать доход через API
        3. Создать расход через API
        4. Получить транзакцию по ID
        5. Получить баланс пользователя
        """
        
        # Step 1: Создание категорий в БД
        from infrastructure.adapter.out.models import CategoryModel
        
        category1 = CategoryModel(
            category_id="CAT-E2E-001",
            user_id="user-e2e",
            name="Накопления",
            balance=0.0,
            budget_percentage=30.0
        )
        category2 = CategoryModel(
            category_id="CAT-E2E-002",
            user_id="user-e2e",
            name="Продукты",
            balance=0.0,
            budget_percentage=70.0
        )
        db_session.add(category1)
        db_session.add(category2)
        await db_session.commit()
        
        # Step 2: Создание дохода
        income_response = client.post(
            "/api/transactions/income",
            json={
                "user_id": "user-e2e",
                "amount": 1000.0,
                "description": "Тестовый доход",
                "idempotency_key": "e2e-income-key"
            }
        )
        
        assert income_response.status_code == 200
        income_data = income_response.json()
        assert "transaction_id" in income_data
        tx_id = income_data["transaction_id"]
        
        # Step 3: Создание расхода
        expense_response = client.post(
            "/api/transactions/expense",
            json={
                "user_id": "user-e2e",
                "category_id": "CAT-E2E-002",
                "amount": 200.0,
                "description": "Покупка продуктов",
                "idempotency_key": "e2e-expense-key"
            }
        )
        
        assert expense_response.status_code == 200
        expense_data = expense_response.json()
        assert "transaction_id" in expense_data
        
        # Step 4: Получение транзакции по ID
        get_response = client.get(f"/api/transactions/{tx_id}")
        
        assert get_response.status_code == 200
        tx_data = get_response.json()
        assert tx_data["transaction_id"] == tx_id
        assert tx_data["amount"] == 1000.0
        assert tx_data["type"] == "INCOME"
        
        # Step 5: Получение баланса пользователя
        balance_response = client.get("/api/users/user-e2e/balance")
        
        assert balance_response.status_code == 200
        balance_data = balance_response.json()
        assert "CAT-E2E-001" in balance_data or "CAT-E2E-002" in balance_data
    
    @pytest.mark.asyncio
    async def test_idempotency_e2e(self, client):
        """E2E тест идемпотентности"""
        
        request_data = {
            "user_id": "user-idem",
            "amount": 500.0,
            "description": "Идемпотентный доход",
            "idempotency_key": "idem-e2e-key"
        }
        
        # Первый запрос
        response1 = client.post("/api/transactions/income", json=request_data)
        tx_id1 = response1.json()["transaction_id"]
        
        # Второй запрос с тем же ключом
        response2 = client.post("/api/transactions/income", json=request_data)
        tx_id2 = response2.json()["transaction_id"]
        
        assert tx_id1 == tx_id2
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_transaction_not_found_e2e(self, client):
        """E2E тест: транзакция не найдена"""
        
        response = client.get("/api/transactions/TXN-NOT-EXIST")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Transaction not found"
    
    @pytest.mark.asyncio
    async def test_list_transactions_e2e(self, client, db_session):
        """E2E тест: список транзакций"""
        
        # Создание нескольких транзакций
        for i in range(3):
            client.post(
                "/api/transactions/income",
                json={
                    "user_id": "user-list-e2e",
                    "amount": 100.0 * (i + 1),
                    "idempotency_key": f"list-e2e-key-{i}"
                }
            )
        
        # Получение списка
        response = client.get(
            "/api/transactions/",
            params={"user_id": "user-list-e2e", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        