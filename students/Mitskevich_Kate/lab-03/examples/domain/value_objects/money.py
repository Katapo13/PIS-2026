from dataclasses import dataclass
from decimal import Decimal

class Money:
    """Value Object: денежная сумма"""
    amount: Decimal
    currency: str = "RUB"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Сумма не может быть отрицательной")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Валюта должна быть 3-х буквенным кодом")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Нельзя складывать разные валюты")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Нельзя вычитать разные валюты")
        return Money(self.amount - other.amount, self.currency)
    
    def multiply(self, percentage: Decimal) -> 'Money':
        """Умножить сумму на процент (0-100)"""
        if not 0 <= percentage <= 100:
            raise ValueError("Процент должен быть от 0 до 100")
        return Money(self.amount * percentage / 100, self.currency)