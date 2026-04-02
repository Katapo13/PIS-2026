from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from enum import Enum


class TransactionTypeDto(str, Enum):
    """DTO перечисление типов транзакций"""
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TransactionStatusDto(str, Enum):
    """DTO перечисление статусов транзакций"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CategoryDistributionDto:
    """DTO распределения по категории"""
    category_id: str
    amount: Decimal
    percentage: float = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_id": self.category_id,
            "amount": float(self.amount),
            "percentage": self.percentage
        }


@dataclass(frozen=True)
class TransactionDto:
    """DTO для чтения данных транзакции"""
    transaction_id: str
    user_id: str
    type: TransactionTypeDto
    amount: Decimal
    description: str
    status: TransactionStatusDto
    created_at: datetime
    category_distributions: List[CategoryDistributionDto]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "type": self.type.value,
            "amount": float(self.amount),
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "category_distributions": [d.to_dict() for d in self.category_distributions]
        }


@dataclass(frozen=True)
class CategoryBalanceDto:
    """DTO баланса категории"""
    category_id: str
    name: str
    balance: Decimal
    budget_percentage: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_id": self.category_id,
            "name": self.name,
            "balance": float(self.balance),
            "budget_percentage": float(self.budget_percentage)
        }