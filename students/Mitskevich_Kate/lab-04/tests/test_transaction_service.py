import pytest
from decimal import Decimal
from unittest.mock import Mock
from datetime import datetime

from application.service.transaction_application_service import TransactionApplicationService
from application.command.create_income_command import CreateIncomeCommand
from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.dto.transaction_dto import TransactionDto, TransactionTypeDto, TransactionStatusDto


class TestTransactionApplicationService:
    """Тесты для TransactionApplicationService (фасада)"""
    
    def test_create_income_delegates_to_handler(self):
        """Тест: метод create_income делегирует вызов обработчику"""
        # Mock handlers
        mock_create_handler = Mock()
        mock_create_handler.handle.return_value = "TXN-2026-00001"
        
        mock_expense_handler = Mock()
        mock_budget_handler = Mock()
        mock_get_handler = Mock()
        mock_list_handler = Mock()
        mock_balance_handler = Mock()
        
        # Создание сервиса
        service = TransactionApplicationService(
            create_income_handler=mock_create_handler,
            create_expense_handler=mock_expense_handler,
            update_budget_handler=mock_budget_handler,
            get_transaction_handler=mock_get_handler,
            list_transactions_handler=mock_list_handler,
            get_balance_handler=mock_balance_handler
        )
        
        # Создание команды
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="test-key"
        )
        
        # Вызов метода
        result = service.create_income(command)
        
        # Проверки
        assert result == "TXN-2026-00001"
        mock_create_handler.handle.assert_called_once_with(command)
    
    def test_get_transaction_delegates_to_handler(self):
        """Тест: метод get_transaction_by_id делегирует вызов обработчику"""
        # Mock handlers
        mock_create_handler = Mock()
        mock_expense_handler = Mock()
        mock_budget_handler = Mock()
        mock_get_handler = Mock()
        mock_list_handler = Mock()
        mock_balance_handler = Mock()
        
        # Настройка mock для get_handler
        expected_dto = TransactionDto(
            transaction_id="TXN-2026-00001",
            user_id="user-001",
            type=TransactionTypeDto.INCOME,
            amount=Decimal("1000"),
            description="Test",
            status=TransactionStatusDto.COMPLETED,
            created_at=datetime(2026, 4, 1),
            category_distributions=[]
        )
        mock_get_handler.handle.return_value = expected_dto
        
        # Создание сервиса
        service = TransactionApplicationService(
            create_income_handler=mock_create_handler,
            create_expense_handler=mock_expense_handler,
            update_budget_handler=mock_budget_handler,
            get_transaction_handler=mock_get_handler,
            list_transactions_handler=mock_list_handler,
            get_balance_handler=mock_balance_handler
        )
        
        # Создание запроса
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-00001")
        
        # Вызов метода
        result = service.get_transaction_by_id(query)
        
        # Проверки
        assert result == expected_dto
        mock_get_handler.handle.assert_called_once_with(query)