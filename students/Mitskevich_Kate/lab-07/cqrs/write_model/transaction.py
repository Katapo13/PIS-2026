from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class TransactionStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class CategoryDistribution:
    category_id: str
    amount: Decimal
    percentage: Optional[Decimal] = None

@dataclass
class Transaction:
    """Aggregate Root: транзакция дохода или расхода"""
    transaction_id: str
    user_id: str
    type: TransactionType
    amount: Decimal
    distributions: List[CategoryDistribution]
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")
        
        if self.type == TransactionType.INCOME:
            self._validate_income_distributions()
        else:
            self._validate_expense_distributions()
    
    def _validate_income_distributions(self):
        """Проверка: сумма распределений дохода = общей сумме"""
        total_distributed = sum(d.amount for d in self.distributions)
        if abs(total_distributed - self.amount) > Decimal("0.01"):
            raise ValueError(
                f"Сумма распределений ({total_distributed}) "
                f"не равна сумме дохода ({self.amount})"
            )
    
    def _validate_expense_distributions(self):
        """Проверка: сумма расходов не превышает сумму по категориям"""
        for dist in self.distributions:
            if dist.amount <= 0:
                raise ValueError("Сумма расхода по категории должна быть положительной")
        
        total = sum(d.amount for d in self.distributions)
        if abs(total - self.amount) > Decimal("0.01"):
            raise ValueError(
                f"Сумма распределений ({total}) "
                f"не равна сумме расхода ({self.amount})"
            )
    
    def complete(self):
        """Завершить транзакцию"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Нельзя завершить транзакцию со статусом {self.status}")
        self.status = TransactionStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def fail(self, reason: str):
        """Отметить транзакцию как неудачную"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Нельзя отменить транзакцию со статусом {self.status}")
        self.status = TransactionStatus.FAILED
        self.description = f"{self.description} [FAILED: {reason}]"
        self.updated_at = datetime.now()
    
    def get_total_by_category(self, category_id: str) -> Decimal:
        """Получить сумму по конкретной категории"""
        for dist in self.distributions:
            if dist.category_id == category_id:
                return dist.amount
        return Decimal("0")