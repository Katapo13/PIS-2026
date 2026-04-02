"""
Infrastructure Layer: Dependency Injection Configuration

Конфигурация Dependency Injection (DI).
Здесь создаются экземпляры адаптеров и сервисов.
"""
from fastapi import FastAPI

from application.port.out import RequestRepository, NotificationService
from application.service import RequestService
from infrastructure.adapter.out import InMemoryRequestRepository, MockSmsService
from infrastructure.adapter.in import RequestController


class DependencyContainer:
    def __init__(self, use_postgres: bool = False):
        if use_postgres:
            self._transaction_repo = PostgreSQLTransactionRepository()
            self._category_repo = PostgreSQLCategoryRepository()
            self._budget_repo = PostgreSQLBudgetRepository()
        else:
            self._transaction_repo = InMemoryTransactionRepository()
            self._category_repo = InMemoryCategoryRepository()
            self._budget_repo = InMemoryBudgetRepository()
    
    def get_transaction_service(self) -> TransactionService:
        return TransactionService(
            self._transaction_repo,
            self._category_repo,
            self._budget_repo
        )