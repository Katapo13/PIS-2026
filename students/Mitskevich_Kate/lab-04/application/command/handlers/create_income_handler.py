from decimal import Decimal
from typing import List, Optional
from domain.aggregates.transaction import Transaction, TransactionType
from domain.entities.category import Category
from domain.value_objects.transaction_id import TransactionId
from domain.value_objects.category_distribution import CategoryDistribution
from domain.events.transaction_events import (
    TransactionCreatedEvent, BalanceUpdatedEvent, EventBus
)
from application.command.create_income_command import CreateIncomeCommand
from application.port.out.transaction_repository import TransactionRepository
from application.port.out.category_repository import CategoryRepository
from application.port.out.budget_settings_repository import BudgetSettingsRepository

class CreateIncomeHandler:
    """Обработчик команды создания дохода"""
    
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        category_repo: CategoryRepository,
        budget_repo: BudgetSettingsRepository,
        event_bus: EventBus
    ):
        self._transaction_repo = transaction_repo
        self._category_repo = category_repo
        self._budget_repo = budget_repo
        self._event_bus = event_bus
    
    def handle(self, command: CreateIncomeCommand) -> str:
        """Обработать команду создания дохода"""
        
        # 1. Проверка идемпотентности
        existing = self._transaction_repo.find_by_idempotency_key(
            command.idempotency_key
        )
        if existing:
            return existing.transaction_id
        
        # 2. Загрузка категорий пользователя
        categories = self._category_repo.find_by_user_id(command.user_id)
        if not categories:
            raise ValueError(f"У пользователя {command.user_id} нет категорий")
        
        # 3. Получение настроек бюджета
        budget_settings = self._budget_repo.find_by_user_id(command.user_id)
        
        # 4. Расчёт распределения дохода
        distributions = self._calculate_distributions(
            command.amount, categories, budget_settings
        )
        
        # 5. Создание транзакции
        transaction_id = TransactionId.generate(command.user_id).value
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=command.user_id,
            type=TransactionType.INCOME,
            amount=command.amount,
            distributions=distributions,
            description=command.description or "",
            idempotency_key=command.idempotency_key
        )
        
        # 6. Сохранение транзакции
        self._transaction_repo.save(transaction)
        
        # 7. Обновление балансов категорий
        for dist in distributions:
            category = self._category_repo.find_by_id(dist.category_id)
            if category:
                old_balance = category.balance
                category.update_balance(dist.amount)
                self._category_repo.update_balance(category.category_id, category.balance)
                
                # Публикация события об изменении баланса
                self._event_bus.publish(BalanceUpdatedEvent(
                    category_id=category.category_id,
                    user_id=command.user_id,
                    old_balance=old_balance,
                    new_balance=category.balance,
                    change_amount=dist.amount
                ))
        
        # 8. Завершение транзакции
        transaction.complete()
        self._transaction_repo.save(transaction)
        
        # 9. Публикация события создания транзакции
        self._event_bus.publish(TransactionCreatedEvent(
            transaction_id=transaction_id,
            user_id=command.user_id,
            transaction_type="INCOME",
            amount=command.amount,
            description=command.description or ""
        ))
        
        return transaction_id
    
    def _calculate_distributions(self, total_amount: Decimal, 
                                  categories: List[Category],
                                  budget_settings) -> List[CategoryDistribution]:
        """Рассчитать распределение дохода по категориям"""
        distributions = []
        
        for category in categories:
            percentage = category.budget_percentage
            if budget_settings:
                percentage = budget_settings.get_percentage(category.category_id) or percentage
            
            if percentage > 0:
                amount = total_amount * percentage / 100
                distributions.append(CategoryDistribution(
                    category_id=category.category_id,
                    amount=amount,
                    percentage=percentage
                ))
        
        # Проверка суммы распределений
        total_distributed = sum(d.amount for d in distributions)
        if abs(total_distributed - total_amount) > Decimal('0.01'):
            # Добавляем остаток в первую категорию
            if distributions:
                diff = total_amount - total_distributed
                first = distributions[0]
                distributions[0] = CategoryDistribution(
                    category_id=first.category_id,
                    amount=first.amount + diff,
                    percentage=first.percentage
                )
        
        return distributions