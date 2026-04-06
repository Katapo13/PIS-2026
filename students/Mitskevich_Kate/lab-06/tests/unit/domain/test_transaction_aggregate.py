import pytest
from decimal import Decimal
from domain.aggregates.transaction import Transaction, TransactionType, TransactionStatus
from domain.value_objects.category_distribution import CategoryDistribution


class TestTransaction:
    def test_income_transaction_creation(self):
        dist = [
            CategoryDistribution("CAT-001", Decimal("600")),
            CategoryDistribution("CAT-002", Decimal("400"))
        ]
        tx = Transaction(
            transaction_id="TXN-2026-00001",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("1000"),
            distributions=dist
        )
        assert tx.status == TransactionStatus.PENDING
        assert tx.amount == Decimal("1000")
    
    def test_income_transaction_distribution_sum_validation(self):
        dist = [CategoryDistribution("CAT-001", Decimal("700"))]
        with pytest.raises(ValueError, match="не равна сумме дохода"):
            Transaction(
                transaction_id="TXN-2026-00002",
                user_id="user-001",
                type=TransactionType.INCOME,
                amount=Decimal("1000"),
                distributions=dist
            )
    
    def test_expense_transaction_creation(self):
        dist = [CategoryDistribution("CAT-001", Decimal("200"))]
        tx = Transaction(
            transaction_id="TXN-2026-00003",
            user_id="user-001",
            type=TransactionType.EXPENSE,
            amount=Decimal("200"),
            distributions=dist
        )
        assert tx.type == TransactionType.EXPENSE
    
    def test_transaction_complete(self):
        dist = [CategoryDistribution("CAT-001", Decimal("100"))]
        tx = Transaction(
            transaction_id="TXN-2026-00004",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("100"),
            distributions=dist
        )
        tx.complete()
        assert tx.status == TransactionStatus.COMPLETED
    
    def test_transaction_cannot_complete_twice(self):
        dist = [CategoryDistribution("CAT-001", Decimal("100"))]
        tx = Transaction(
            transaction_id="TXN-2026-00005",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("100"),
            distributions=dist
        )
        tx.complete()
        with pytest.raises(ValueError, match="Нельзя завершить"):
            tx.complete()
    
    def test_transaction_fail(self):
        dist = [CategoryDistribution("CAT-001", Decimal("100"))]
        tx = Transaction(
            transaction_id="TXN-2026-00006",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("100"),
            distributions=dist
        )
        tx.fail("Ошибка валидации")
        assert tx.status == TransactionStatus.FAILED
        assert "FAILED" in tx.description
        