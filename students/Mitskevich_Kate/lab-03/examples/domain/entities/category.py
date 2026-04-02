from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Category:
    """Entity: категория для группировки транзакций"""
    category_id: str
    user_id: str
    name: str
    budget_percentage: Decimal
    balance: Decimal = Decimal("0")
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if not self.name or len(self.name) > 50:
            raise ValueError("Название категории должно быть от 1 до 50 символов")
        if not 0 <= self.budget_percentage <= 100:
            raise ValueError("Процент бюджета должен быть от 0 до 100")
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_balance(self, amount: Decimal) -> None:
        """Обновить баланс категории"""
        self.balance += amount
        self.updated_at = datetime.now()
    
    def can_spend(self, amount: Decimal) -> bool:
        """Проверить, можно ли потратить указанную сумму"""
        return self.balance >= amount
    
    def __eq__(self, other):
        """Сравнение по ID (identity)"""
        if not isinstance(other, Category):
            return False
        return self.category_id == other.category_id