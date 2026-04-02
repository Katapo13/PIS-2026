import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.dto.transaction_dto import (
    TransactionDto, TransactionTypeDto, TransactionStatusDto, 
    CategoryDistributionDto, CategoryBalanceDto
)


class TestGetTransactionByIdQuery:
    """Тесты для запроса GetTransactionByIdQuery"""
    
    def test_valid_query_creation(self):
        """Тест создания валидного запроса"""
        query = GetTransactionByIdQuery(transaction_id="TXN-2026-00001")
        assert query.transaction_id == "TXN-2026-00001"
    
    def test_empty_transaction_id(self):
        """Тест: пустой transaction_id"""
        with pytest.raises(ValueError, match="transaction_id обязателен"):
            GetTransactionByIdQuery(transaction_id="")


class TestTransactionDto:
    """Тесты для TransactionDto"""
    
    def test_transaction_dto_creation(self):
        """Тест создания TransactionDto"""
        distributions = [
            CategoryDistributionDto(category_id="CAT-001", amount=Decimal("600"), percentage=60),
            CategoryDistributionDto(category_id="CAT-002", amount=Decimal("400"), percentage=40)
        ]
        
        dto = TransactionDto(
            transaction_id="TXN-2026-00001",
            user_id="user-001",
            type=TransactionTypeDto.INCOME,
            amount=Decimal("1000"),
            description="Зарплата",
            status=TransactionStatusDto.COMPLETED,
            created_at=datetime(2026, 4, 1),
            category_distributions=distributions
        )
        
        assert dto.transaction_id == "TXN-2026-00001"
        assert dto.user_id == "user-001"
        assert dto.type == TransactionTypeDto.INCOME
        assert dto.amount == Decimal("1000")
        assert dto.description == "Зарплата"
        assert dto.status == TransactionStatusDto.COMPLETED
        assert len(dto.category_distributions) == 2
    
    def test_transaction_dto_to_dict(self):
        """Тест конвертации в словарь"""
        distributions = [
            CategoryDistributionDto(category_id="CAT-001", amount=Decimal("600"), percentage=60)
        ]
        
        dto = TransactionDto(
            transaction_id="TXN-2026-00001",
            user_id="user-001",
            type=TransactionTypeDto.INCOME,
            amount=Decimal("1000"),
            description="Зарплата",
            status=TransactionStatusDto.COMPLETED,
            created_at=datetime(2026, 4, 1, 12, 0, 0),
            category_distributions=distributions
        )
        
        result = dto.to_dict()
        
        assert result["transaction_id"] == "TXN-2026-00001"
        assert result["user_id"] == "user-001"
        assert result["amount"] == 1000.0
        assert result["type"] == "INCOME"
        assert result["status"] == "COMPLETED"
        assert "created_at" in result
        assert len(result["category_distributions"]) == 1
    
    def test_category_distribution_dto_to_dict(self):
        """Тест конвертации CategoryDistributionDto"""
        dist = CategoryDistributionDto(
            category_id="CAT-001", 
            amount=Decimal("500"), 
            percentage=50
        )
        
        result = dist.to_dict()
        
        assert result["category_id"] == "CAT-001"
        assert result["amount"] == 500.0
        assert result["percentage"] == 50
    
    def test_category_balance_dto(self):
        """Тест CategoryBalanceDto"""
        dto = CategoryBalanceDto(
            category_id="CAT-001",
            name="Продукты",
            balance=Decimal("5000"),
            budget_percentage=Decimal("30")
        )
        
        assert dto.category_id == "CAT-001"
        assert dto.name == "Продукты"
        assert dto.balance == Decimal("5000")
        assert dto.budget_percentage == Decimal("30")
        
        result = dto.to_dict()
        assert result["category_id"] == "CAT-001"
        assert result["balance"] == 5000.0