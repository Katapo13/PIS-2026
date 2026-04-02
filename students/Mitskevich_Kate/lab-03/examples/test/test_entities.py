import pytest
from decimal import Decimal
from domain.entities.category import Category
from domain.entities.budget_settings import BudgetSettings

def test_category_creation():
    cat = Category(
        category_id="CAT-001",
        user_id="user-001",
        name="Продукты",
        budget_percentage=Decimal("30"),
        balance=Decimal("5000")
    )
    assert cat.name == "Продукты"
    assert cat.budget_percentage == Decimal("30")

def test_category_equality_by_id():
    cat1 = Category("CAT-001", "user-001", "Продукты", Decimal("30"))
    cat2 = Category("CAT-001", "user-001", "Еда", Decimal("40"))  # Другое имя
    cat3 = Category("CAT-002", "user-001", "Продукты", Decimal("30"))
    
    assert cat1 == cat2  # Одинаковый ID
    assert cat1 != cat3  # Разные ID

def test_category_update_balance():
    cat = Category("CAT-001", "user-001", "Продукты", Decimal("30"), balance=Decimal("1000"))
    cat.update_balance(Decimal("500"))
    assert cat.balance == Decimal("1500")

def test_budget_settings_validation():
    settings = BudgetSettings("user-001", {
        "CAT-001": Decimal("60"),
        "CAT-002": Decimal("40")
    })
    assert settings.get_percentage("CAT-001") == Decimal("60")

def test_budget_settings_invalid_total():
    with pytest.raises(ValueError, match="100%"):
        BudgetSettings("user-001", {
            "CAT-001": Decimal("70"),
            "CAT-002": Decimal("40")
        })