import pytest
from decimal import Decimal
from domain.entities.category import Category


class TestCategory:
    def test_category_creation(self):
        cat = Category(
            category_id="CAT-001",
            user_id="user-001",
            name="Продукты",
            budget_percentage=Decimal("30"),
            balance=Decimal("5000")
        )
        assert cat.name == "Продукты"
        assert cat.budget_percentage == Decimal("30")
    
    def test_category_equality_by_id(self):
        cat1 = Category("CAT-001", "user-001", "Продукты", Decimal("30"))
        cat2 = Category("CAT-001", "user-001", "Еда", Decimal("40"))
        cat3 = Category("CAT-002", "user-001", "Продукты", Decimal("30"))
        
        assert cat1 == cat2  # Одинаковый ID
        assert cat1 != cat3  # Разные ID
    
    def test_update_balance(self):
        cat = Category("CAT-001", "user-001", "Продукты", Decimal("30"), balance=Decimal("1000"))
        cat.update_balance(Decimal("500"))
        assert cat.balance == Decimal("1500")
    
    def test_can_spend_success(self):
        cat = Category("CAT-001", "user-001", "Продукты", Decimal("30"), balance=Decimal("1000"))
        assert cat.can_spend(Decimal("500")) is True
    
    def test_can_spend_failure(self):
        cat = Category("CAT-001", "user-001", "Продукты", Decimal("30"), balance=Decimal("100"))
        assert cat.can_spend(Decimal("500")) is False