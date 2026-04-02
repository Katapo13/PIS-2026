import pytest
from decimal import Decimal
from unittest.mock import Mock
from datetime import datetime

from application.command.create_income_command import CreateIncomeCommand
from application.command.handlers.create_income_handler import CreateIncomeHandler
from domain.aggregates.transaction import Transaction, TransactionType
from domain.entities.category import Category
from domain.value_objects.category_distribution import CategoryDistribution


class TestCreateIncomeHandler:
    """Тесты для CreateIncomeHandler"""
    
    def test_create_income_success(self):
        """Тест успешного создания дохода"""
        # Mock репозиториев
        mock_tx_repo = Mock()
        mock_category_repo = Mock()
        mock_budget_repo = Mock()
        mock_event_bus = Mock()
        
        # Настройка моков
        mock_tx_repo.find_by_idempotency_key.return_value = None
        
        categories = [
            Category(category_id="CAT-001", user_id="user-001", name="Накопления", 
                     budget_percentage=Decimal("30"), balance=Decimal("0")),
            Category(category_id="CAT-002", user_id="user-001", name="Продукты", 
                     budget_percentage=Decimal("70"), balance=Decimal("0"))
        ]
        mock_category_repo.find_by_user_id.return_value = categories
        mock_budget_repo.find_by_user_id.return_value = None
        
        def find_by_id(category_id):
            return next((c for c in categories if c.category_id == category_id), None)
        mock_category_repo.find_by_id.side_effect = find_by_id
        
        # Создание команды
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            description="Зарплата",
            idempotency_key="income-key-001"
        )
        
        # Создание обработчика
        handler = CreateIncomeHandler(
            mock_tx_repo, mock_category_repo, mock_budget_repo, mock_event_bus
        )
        
        # Выполнение
        result = handler.handle(command)
        
        # Проверки
        assert result is not None
        assert result.startswith("TXN-")
        
        # Проверка сохранения транзакции (2 раза: начальное и завершённое состояние)
        assert mock_tx_repo.save.call_count >= 2
        
        # Проверка обновления балансов категорий
        assert mock_category_repo.update_balance.call_count == 2
        
        # Проверка публикации событий (2 баланса + 1 транзакция)
        assert mock_event_bus.publish.call_count >= 3
    
    def test_create_income_idempotency(self):
        """Тест: идемпотентность - повторный запрос возвращает существующую транзакцию"""
        mock_tx_repo = Mock()
        mock_category_repo = Mock()
        mock_budget_repo = Mock()
        mock_event_bus = Mock()
        
        existing_transaction = Mock()
        existing_transaction.transaction_id = "TXN-2026-00001"
        mock_tx_repo.find_by_idempotency_key.return_value = existing_transaction
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="same-key"
        )
        
        handler = CreateIncomeHandler(
            mock_tx_repo, mock_category_repo, mock_budget_repo, mock_event_bus
        )
        
        result = handler.handle(command)
        
        assert result == "TXN-2026-00001"
        # Не должен создавать новую транзакцию
        assert mock_tx_repo.save.call_count == 0
        assert mock_category_repo.update_balance.call_count == 0
        assert mock_event_bus.publish.call_count == 0
    
    def test_create_income_no_categories(self):
        """Тест: у пользователя нет категорий - ошибка"""
        mock_tx_repo = Mock()
        mock_category_repo = Mock()
        mock_budget_repo = Mock()
        mock_event_bus = Mock()
        
        mock_tx_repo.find_by_idempotency_key.return_value = None
        mock_category_repo.find_by_user_id.return_value = []
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="income-key-002"
        )
        
        handler = CreateIncomeHandler(
            mock_tx_repo, mock_category_repo, mock_budget_repo, mock_event_bus
        )
        
        with pytest.raises(ValueError, match="нет категорий"):
            handler.handle(command)
    
    def test_create_income_distribution_calculation(self):
        """Тест: проверка правильности расчёта распределения"""
        mock_tx_repo = Mock()
        mock_category_repo = Mock()
        mock_budget_repo = Mock()
        mock_event_bus = Mock()
        
        mock_tx_repo.find_by_idempotency_key.return_value = None
        
        categories = [
            Category(category_id="CAT-001", user_id="user-001", name="Накопления", 
                     budget_percentage=Decimal("25"), balance=Decimal("0")),
            Category(category_id="CAT-002", user_id="user-001", name="Продукты", 
                     budget_percentage=Decimal("75"), balance=Decimal("0"))
        ]
        mock_category_repo.find_by_user_id.return_value = categories
        mock_budget_repo.find_by_user_id.return_value = None
        
        # Сохраняем созданную транзакцию для проверки
        saved_transaction = None
        def save_transaction(tx):
            nonlocal saved_transaction
            saved_transaction = tx
        
        mock_tx_repo.save.side_effect = save_transaction
        
        def find_by_id(category_id):
            return next((c for c in categories if c.category_id == category_id), None)
        mock_category_repo.find_by_id.side_effect = find_by_id
        
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000"),
            idempotency_key="income-key-003"
        )
        
        handler = CreateIncomeHandler(
            mock_tx_repo, mock_category_repo, mock_budget_repo, mock_event_bus
        )
        
        handler.handle(command)
        
        # Проверка распределения
        assert saved_transaction is not None
        assert saved_transaction.amount == Decimal("1000")
        assert len(saved_transaction.distributions) == 2
        
        # Сумма распределений должна равняться общей сумме
        total_distributed = sum(d.amount for d in saved_transaction.distributions)
        assert total_distributed == Decimal("1000")
    
    def test_calculate_distributions_corrects_rounding(self):
        """Тест: корректировка распределения при ошибках округления"""
        handler = CreateIncomeHandler(Mock(), Mock(), Mock(), Mock())
        
        categories = [
            Category(category_id="CAT-001", user_id="user-001", name="Cat1", 
                     budget_percentage=Decimal("33.33"), balance=Decimal("0")),
            Category(category_id="CAT-002", user_id="user-001", name="Cat2", 
                     budget_percentage=Decimal("33.33"), balance=Decimal("0")),
            Category(category_id="CAT-003", user_id="user-001", name="Cat3", 
                     budget_percentage=Decimal("33.34"), balance=Decimal("0"))
        ]
        
        # Вызов приватного метода для теста
        distributions = handler._calculate_distributions(
            Decimal("1000"), categories, None
        )
        
        total = sum(d.amount for d in distributions)
        assert total == Decimal("1000")