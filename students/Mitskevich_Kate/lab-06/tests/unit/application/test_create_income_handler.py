import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from application.command.create_income_command import CreateIncomeCommand
from application.command.handlers.create_income_handler import CreateIncomeHandler
from domain.aggregates.transaction import Transaction, TransactionType
from domain.entities.category import Category


class TestCreateIncomeHandler:
    
    @pytest.fixture
    def mock_repositories(self):
        return {
            "transaction_repo": Mock(),
            "category_repo": Mock(),
            "budget_repo": Mock(),
            "event_bus": Mock()
        }
    
    @pytest.fixture
    def handler(self, mock_repositories):
        return CreateIncomeHandler(
            transaction_repo=mock_repositories["transaction_repo"],
            category_repo=mock_repositories["category_repo"],
            budget_repo=mock_repositories["budget_repo"],
            event_bus=mock_repositories["event_bus"]
        )
    
    @pytest.mark.asyncio
    async def test_create_income_success(self, handler, mock_repositories):
        # Arrange
        mock_repositories["transaction_repo"].find_by_idempotency_key.return_value = None
        
        categories = [
            Category("CAT-001", "user-001", "Накопления", Decimal("30"), Decimal("0")),
            Category("CAT-002", "user-001", "Продукты", Decimal("70"), Decimal("0"))
        ]
        mock_repositories["category_repo"].find_by_user_id.return_value = categories
        mock_repositories["budget_repo"].find_by_user_id.return_value = None
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            description="Зарплата",
            idempotency_key="test-key-001"
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result is not None
        assert result.startswith("TXN-")
        assert mock_repositories["transaction_repo"].save.call_count >= 2
        assert mock_repositories["category_repo"].update_balance.call_count == 2
        assert mock_repositories["event_bus"].publish.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_create_income_idempotency(self, handler, mock_repositories):
        # Arrange
        existing_transaction = Mock()
        existing_transaction.transaction_id = "TXN-2026-00001"
        mock_repositories["transaction_repo"].find_by_idempotency_key.return_value = existing_transaction
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="same-key"
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result == "TXN-2026-00001"
        assert mock_repositories["transaction_repo"].save.call_count == 0
    
    @pytest.mark.asyncio
    async def test_create_income_no_categories(self, handler, mock_repositories):
        # Arrange
        mock_repositories["transaction_repo"].find_by_idempotency_key.return_value = None
        mock_repositories["category_repo"].find_by_user_id.return_value = []
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="test-key-002"
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="нет категорий"):
            await handler.handle(command)
    
    @pytest.mark.asyncio
    async def test_calculate_distributions(self, handler):
        # Arrange
        categories = [
            Category("CAT-001", "user-001", "Накопления", Decimal("25"), Decimal("0")),
            Category("CAT-002", "user-001", "Продукты", Decimal("75"), Decimal("0"))
        ]
        
        # Act
        distributions = handler._calculate_distributions(Decimal("1000"), categories, None)
        
        # Assert
        assert len(distributions) == 2
        total = sum(d.amount for d in distributions)
        assert total == Decimal("1000")
        