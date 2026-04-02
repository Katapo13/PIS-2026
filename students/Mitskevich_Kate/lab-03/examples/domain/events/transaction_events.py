from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Callable
from enum import Enum

class EventType(Enum):
    TRANSACTION_CREATED = "transaction.created"
    BALANCE_UPDATED = "balance.updated"
    BUDGET_WARNING = "budget.warning"

@dataclass
class DomainEvent:
    """Базовый класс для доменных событий"""
    event_type: EventType
    aggregate_id: str
    occurred_at: datetime = field(default_factory=datetime.now)

@dataclass
class TransactionCreatedEvent(DomainEvent):
    """Событие: создана транзакция"""
    user_id: str
    transaction_type: str
    amount: Decimal
    
    def __init__(self, transaction_id: str, user_id: str, transaction_type: str, amount: Decimal):
        super().__init__(EventType.TRANSACTION_CREATED, transaction_id)
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.amount = amount

@dataclass
class BalanceUpdatedEvent(DomainEvent):
    """Событие: обновлён баланс категории"""
    user_id: str
    category_id: str
    old_balance: Decimal
    new_balance: Decimal
    
    def __init__(self, category_id: str, user_id: str, old_balance: Decimal, new_balance: Decimal):
        super().__init__(EventType.BALANCE_UPDATED, category_id)
        self.user_id = user_id
        self.category_id = category_id
        self.old_balance = old_balance
        self.new_balance = new_balance

# Простой in-memory Event Bus
class EventBus:
    def __init__(self):
        self._handlers: dict = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent):
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                handler(event)