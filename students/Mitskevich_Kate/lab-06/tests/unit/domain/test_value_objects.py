import pytest
from decimal import Decimal
from domain.value_objects.money import Money
from domain.value_objects.transaction_id import TransactionId
from domain.value_objects.category_distribution import CategoryDistribution


class TestMoney:
    def test_money_creation(self):
        money = Money(Decimal("100.50"), "RUB")
        assert money.amount == Decimal("100.50")
        assert money.currency == "RUB"
    
    def test_money_cannot_be_negative(self):
        with pytest.raises(ValueError, match="не может быть отрицательной"):
            Money(Decimal("-10"), "RUB")
    
    def test_money_addition(self):
        m1 = Money(Decimal("100"), "RUB")
        m2 = Money(Decimal("50"), "RUB")
        result = m1 + m2
        assert result.amount == Decimal("150")
    
    def test_money_multiply_by_percentage(self):
        money = Money(Decimal("1000"), "RUB")
        result = money.multiply(Decimal("30"))
        assert result.amount == Decimal("300")


class TestTransactionId:
    def test_valid_transaction_id(self):
        tx_id = TransactionId("TXN-2026-00042")
        assert tx_id.year == 2026
        assert tx_id.number == 42
    
    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Неверный формат"):
            TransactionId("INVALID-2026-00001")
    
    def test_future_year(self):
        with pytest.raises(ValueError, match="не может быть в будущем"):
            TransactionId(f"TXN-2030-00001")


class TestCategoryDistribution:
    def test_valid_distribution(self):
        dist = CategoryDistribution("CAT-001", Decimal("500"), Decimal("50"))
        assert dist.category_id == "CAT-001"
        assert dist.amount == Decimal("500")
    
    def test_zero_amount_invalid(self):
        with pytest.raises(ValueError, match="положительной"):
            CategoryDistribution("CAT-001", Decimal("0"))
    
    def test_invalid_percentage(self):
        with pytest.raises(ValueError, match="от 0 до 100"):
            CategoryDistribution("CAT-001", Decimal("500"), Decimal("150"))