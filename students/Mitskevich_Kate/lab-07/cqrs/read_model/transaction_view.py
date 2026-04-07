from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class TransactionView:
    """Денормализованное представление транзакции"""
    transaction_id: str
    user_id: str
    transaction_type: str
    amount: Decimal
    description: str
    status: str
    created_at: datetime
    category_names: str  # Уже JOIN'нутые названия категорий
    total_categories: int
    
    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "type": self.transaction_type,
            "amount": float(self.amount),
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "categories": self.category_names,
            "categories_count": self.total_categories
        }


@dataclass
class UserBalanceView:
    """Денормализованный баланс пользователя"""
    user_id: str
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    last_transaction_at: Optional[datetime]
    transaction_count: int
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "total_income": float(self.total_income),
            "total_expense": float(self.total_expense),
            "balance": float(self.balance),
            "last_transaction": self.last_transaction_at.isoformat() if self.last_transaction_at else None,
            "transaction_count": self.transaction_count
        }


@dataclass
class CategoryStatisticsView:
    """Статистика по категории"""
    category_id: str
    category_name: str
    total_income: Decimal
    total_expense: Decimal
    current_balance: Decimal
    budget_percentage: Decimal
    transaction_count: int
    budget_used_percentage: float  # (expense / budget) * 100
    
    def to_dict(self):
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "total_income": float(self.total_income),
            "total_expense": float(self.total_expense),
            "current_balance": float(self.current_balance),
            "budget_percentage": float(self.budget_percentage),
            "transaction_count": self.transaction_count,
            "budget_used_percentage": self.budget_used_percentage
        }
    