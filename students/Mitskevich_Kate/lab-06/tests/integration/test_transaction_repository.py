import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from infrastructure.adapter.out.postgres_transaction_repository import PostgresTransactionRepository
from infrastructure.adapter.out.models import Base, TransactionModel
from domain.aggregates.transaction import Transaction, TransactionType
from domain.value_objects.category_distribution import CategoryDistribution


class TestTransactionRepository:
    
    @pytest.fixture(scope="class")
    def postgres_container(self):
        with PostgresContainer("postgres:15-alpine") as container:
            yield container
    
    @pytest.fixture
    async def session(self, postgres_container):
        # Подключение к тестовой БД
        database_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(database_url, echo=True)
        
        # Создание таблиц
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Создание сессии
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session
        
        # Очистка
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    @pytest.fixture
    def repository(self, session):
        return PostgresTransactionRepository(session)
    
    @pytest.mark.asyncio
    async def test_save_transaction(self, repository, session):
        # Arrange
        dist = [
            CategoryDistribution("CAT-001", Decimal("600")),
            CategoryDistribution("CAT-002", Decimal("400"))
        ]
        transaction = Transaction(
            transaction_id="TXN-INTEG-001",
            user_id="user-test",
            type=TransactionType.INCOME,
            amount=Decimal("1000"),
            distributions=dist,
            description="Интеграционный тест",
            idempotency_key="integ-key-001"
        )
        
        # Act
        await repository.save(transaction)
        
        # Assert
        result = await session.execute(
            select(TransactionModel).where(
                TransactionModel.transaction_id == "TXN-INTEG-001"
            )
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.amount == 1000.0
        assert saved.user_id == "user-test"
        assert saved.idempotency_key == "integ-key-001"
    
    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, session):
        # Arrange
        dist = [CategoryDistribution("CAT-001", Decimal("500"))]
        transaction = Transaction(
            transaction_id="TXN-INTEG-002",
            user_id="user-test",
            type=TransactionType.EXPENSE,
            amount=Decimal("500"),
            distributions=dist,
            idempotency_key="integ-key-002"
        )
        await repository.save(transaction)
        
        # Act
        found = await repository.find_by_id("TXN-INTEG-002")
        
        # Assert
        assert found is not None
        assert found.transaction_id == "TXN-INTEG-002"
        assert found.amount == Decimal("500")
    
    @pytest.mark.asyncio
    async def test_find_by_idempotency_key(self, repository, session):
        # Arrange
        dist = [CategoryDistribution("CAT-001", Decimal("300"))]
        transaction = Transaction(
            transaction_id="TXN-INTEG-003",
            user_id="user-test",
            type=TransactionType.INCOME,
            amount=Decimal("300"),
            distributions=dist,
            idempotency_key="unique-idem-key"
        )
        await repository.save(transaction)
        
        # Act
        found = await repository.find_by_idempotency_key("unique-idem-key")
        
        # Assert
        assert found is not None
        assert found.idempotency_key == "unique-idem-key"
    
    @pytest.mark.asyncio
    async def test_find_by_user_id_with_pagination(self, repository, session):
        # Arrange
        for i in range(5):
            dist = [CategoryDistribution("CAT-001", Decimal("100"))]
            transaction = Transaction(
                transaction_id=f"TXN-INTEG-00{i}",
                user_id="user-pagination",
                type=TransactionType.INCOME,
                amount=Decimal("100"),
                distributions=dist,
                idempotency_key=f"pagination-key-{i}"
            )
            await repository.save(transaction)
        
        # Act
        results = await repository.find_by_user_id("user-pagination", limit=3, offset=0)
        
        # Assert
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_find_by_user_id_with_filters(self, repository, session):
        # Arrange
        dist = [CategoryDistribution("CAT-001", Decimal("200"))]
        transaction = Transaction(
            transaction_id="TXN-INTEG-FILTER",
            user_id="user-filter",
            type=TransactionType.EXPENSE,
            amount=Decimal("200"),
            distributions=dist,
            idempotency_key="filter-key"
        )
        await repository.save(transaction)
        
        # Act
        results = await repository.find_by_user_id(
            "user-filter",
            transaction_type="EXPENSE"
        )
        
        # Assert
        assert len(results) >= 1
        assert results[0].type == TransactionType.EXPENSE
        