from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum

class TransactionTypeDto(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class TransactionStatusDto(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

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
    category_distributions: list  # Список распределений по категориям

@dataclass(frozen=True)
class ListUserTransactionsQuery:
    """Запрос списка транзакций пользователя"""
    user_id: str
    limit: int = 50
    offset: int = 0
    transaction_type: Optional[TransactionTypeDto] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.user_id:
            raise ValueError("user_id обязателен")
        if self.limit < 1 or self.limit > 100:
            raise ValueError("limit должен быть от 1 до 100")
        if self.offset < 0:
            raise ValueError("offset не может быть отрицательным")