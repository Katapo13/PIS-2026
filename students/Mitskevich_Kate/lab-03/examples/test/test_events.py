import pytest
from decimal import Decimal
from domain.events.transaction_events import (
    TransactionCreatedEvent, TransactionCompletedEvent,
    BalanceUpdatedEvent, BudgetWarningEvent, EventBus
)

def test_transaction_created_event():
    event = TransactionCreatedEvent(
        "TXN-2026-00001", "user-001", "INCOME", Decimal("1000"), "Зарплата"
    )
    
    assert event.event_type.value == "transaction.created"
    assert event.user_id == "user-001"
    assert event.amount == Decimal("1000")
    
    data = event.to_dict()
    assert data["transaction_type"] == "INCOME"
    assert data["amount"] == 1000.0

def test_balance_updated_event():
    event = BalanceUpdatedEvent(
        "CAT-001", "user-001", Decimal("500"), Decimal("700"), Decimal("200")
    )
    
    assert event.old_balance == Decimal("500")
    assert event.new_balance == Decimal("700")
    assert event.change_amount == Decimal("200")

def test_budget_warning_event():
    event = BudgetWarningEvent(
        "CAT-001", "user-001", "Продукты", Decimal("100"), Decimal("500")
    )
    
    assert event.current_balance == Decimal("100")
    assert event.threshold == Decimal("500")

def test_event_bus():
    bus = EventBus()
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    bus.subscribe(TransactionCreatedEvent.event_type, handler)
    
    event = TransactionCreatedEvent("TXN-001", "user-001", "EXPENSE", Decimal("500"))
    bus.publish(event)
    
    assert len(received_events) == 1
    assert received_events[0].aggregate_id == "TXN-001"

def test_event_bus_multiple_handlers():
    bus = EventBus()
    results = []
    
    def handler1(event):
        results.append("handler1")
    
    def handler2(event):
        results.append("handler2")
    
    bus.subscribe(TransactionCompletedEvent.event_type, handler1)
    bus.subscribe(TransactionCompletedEvent.event_type, handler2)
    
    event = TransactionCompletedEvent("TXN-001", "user-001", "INCOME")
    bus.publish(event)
    
    assert len(results) == 2
    assert "handler1" in results
    assert "handler2" in results