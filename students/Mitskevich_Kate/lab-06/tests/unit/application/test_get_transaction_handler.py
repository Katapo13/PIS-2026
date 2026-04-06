import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.handlers.get_transaction_by_id_handler import GetTransactionByIdHandler
from application.query.dto.transaction_dto import TransactionTypeDto, TransactionStatusDto


class TestGetTransactionByIdHandler:
    
    @pytest.fixture
    def mock_repo(self):
        return Mock()
    
    @pytest.fixture
    def handler(self, mock_repo):
        return GetTransactionByIdHandler(mock_repo)
    
    @pytest.mark.asyncio
    async def test_get_transaction_found(self, handler, mock_repo):
        # Arrange
        mock_transaction = Mock()
        mock_transaction.transaction_id = "TXN-2026-00001"
        mock_transaction.user_id = "user-001"
        mock_transaction.type.value = "INCOME"
        mock_transaction.amount = Decimal("1000")
        mock_transaction.description = "Зарплата"
        mock_transaction.status.value = "COMPLETED"
        mock_transaction.created_at = datetime(2026, 4, 1)
        mock_transaction.distributions = []
        
        mock_repo.find_by_id.return_value = mock_transaction
        
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-00001")
        
        # Act
        result = await handler.handle(query)
        
        # Assert
        assert result is not None
        assert result.transaction_id == "TXN-2026-00001"
        assert result.type == TransactionTypeDto.INCOME
        mock_repo.find_by_id.assert_called_once_with("TXN-2026-00001")
    
    @pytest.mark.asyncio
    async def test_get_transaction_not_found(self, handler, mock_repo):
        # Arrange
        mock_repo.find_by_id.return_value = None
        query = GetTransactionByIdQuery(transaction_id="TXN-9999-99999")
        
        # Act
        result = await handler.handle(query)
        
        # Assert
        assert result is None
        