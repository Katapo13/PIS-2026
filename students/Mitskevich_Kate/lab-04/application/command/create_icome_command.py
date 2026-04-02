from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class CreateIncomeCommand:
    """Команда для регистрации дохода"""
    user_id: str
    amount: Decimal
    description: Optional[str] = None
    idempotency_key: str = ""
    source: Optional[str] = None
    
    def __post_init__(self):
        if not self.user_id or len(self.user_id) < 3:
            raise ValueError("user_id должен быть не менее 3 символов")
        if self.amount <= 0:
            raise ValueError("Сумма дохода должна быть положительной")
        if not self.idempotency_key:
            raise ValueError("idempotency_key обязателен")