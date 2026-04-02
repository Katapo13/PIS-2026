import pytest
from decimal import Decimal
from unittest.mock import Mock
from datetime import datetime

from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.handlers.get_transaction_by_id_handler import GetTransactionByIdHandler
from application.query.dto.transaction_dto import TransactionTypeDto, TransactionStatusDto


class TestGetTransactionByIdHandler:
    """Тесты для GetTransactionByIdHandler"""
    
    def test_handle_transaction_found(self):
        """Тест: транзакция найдена"""
        # Mock репозитория
        mock_repo = Mock()
        
        # Создаём mock транзакции
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
        
        # Создание обработчика
        handler = GetTransactionByIdHandler(mock_repo)
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-00001")
        
        # Выполнение
        result = handler.handle(query)
        
        # Проверки
        assert result is not None
        assert result.transaction_id == "TXN-2026-00001"
        assert result.user_id == "user-001"
        assert result.type == TransactionTypeDto.INCOME
        assert result.amount == Decimal("1000")
        assert result.description == "Зарплата"
        assert result.status == TransactionStatusDto.COMPLETED
        
        mock_repo.find_by_id.assert_called_once_with("TXN-2026-00001")
    
    def test_handle_transaction_not_found(self):
        """Тест: транзакция не найдена"""
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = None
        
        handler = GetTransactionByIdHandler(mock_repo)
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-99999")
        
        result = handler.handle(query)
        
        assert result is None
        mock_repo.find_by_id.assert_called_once_with("TXN-2026-99999")
    
    def test_handle_with_category_distributions(self):
        """Тест: транзакция с распределением по категориям"""
        mock_repo = Mock()
        
        # Создаём mock распределений
        mock_distribution1 = Mock()
        mock_distribution1.category_id = "CAT-001"
        mock_distribution1.amount = Decimal("600")
        mock_distribution1.percentage = Decimal("60")
        
        mock_distribution2 = Mock()
        mock_distribution2.category_id = "CAT-002"
        mock_distribution2.amount = Decimal("400")
        mock_distribution2.percentage = Decimal("40")
        
        # Создаём mock транзакции
        mock_transaction = Mock()
        mock_transaction.transaction_id = "TXN-2026-00002"
        mock_transaction.user_id = "user-001"
        mock_transaction.type.value = "INCOME"
        mock_transaction.amount = Decimal("1000")
        mock_transaction.description = "Зарплата"
        mock_transaction.status.value = "COMPLETED"
        mock_transaction.created_at = datetime(2026, 4, 1)
        mock_transaction.distributions = [mock_distribution1, mock_distribution2]
        
        mock_repo.find_by_id.return_value = mock_transaction
        
        handler = GetTransactionByIdHandler(mock_repo)
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-00002")
        
        result = handler.handle(query)
        
        assert result is not None
        assert len(result.category_distributions) == 2
        assert result.category_distributions[0]["category_id"] == "CAT-001"
        assert result.category_distributions[0]["amount"] == Decimal("600")