from typing import Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from domain.events.transaction_events import (
    TransactionCreatedEvent, 
    TransactionCompletedEvent,
    BalanceUpdatedEvent
)
from cqrs.read_model.transaction_view import TransactionView
from infrastructure.adapter.out.models import (
    TransactionViewModel, 
    UserBalanceViewModel,
    CategoryStatisticsViewModel
)

class TransactionProjection:
    """
    Проекция для синхронизации Write Model и Read Model
    Обрабатывает доменные события и обновляет денормализованные view
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def on_transaction_created(self, event: TransactionCreatedEvent):
        """Обработчик события создания транзакции"""
        
        # 1. Создание TransactionView
        # Формируем строку с названиями категорий
        category_names = ", ".join([
            f"{dist['category_id']}: {dist['amount']}" 
            for dist in event.category_distributions
        ])
        
        view = TransactionViewModel(
            transaction_id=event.transaction_id,
            user_id=event.user_id,
            transaction_type=event.transaction_type,
            amount=float(event.amount),
            description=event.description,
            status="PENDING",
            created_at=event.occurred_at,
            category_names=category_names,
            total_categories=len(event.category_distributions)
        )
        self._session.add(view)
        
        # 2. Обновление UserBalanceView
        await self._update_user_balance(
            event.user_id, 
            event.transaction_type, 
            event.amount
        )
        
        # 3. Обновление CategoryStatisticsView
        for dist in event.category_distributions:
            await self._update_category_statistics(
                event.user_id,
                dist["category_id"],
                event.transaction_type,
                Decimal(str(dist["amount"]))
            )
        
        await self._session.commit()
    
    async def on_transaction_completed(self, event):
        """Обработчик завершения транзакции"""
        
        await self._session.execute(
            update(TransactionViewModel)
            .where(TransactionViewModel.transaction_id == event.transaction_id)
            .values(status="COMPLETED")
        )
        await self._session.commit()
    
    async def on_balance_updated(self, event: BalanceUpdatedEvent):
        """Обработчик обновления баланса"""
        
        # Обновляем баланс в CategoryStatisticsView
        stmt = select(CategoryStatisticsViewModel).where(
            CategoryStatisticsViewModel.user_id == event.user_id,
            CategoryStatisticsViewModel.category_id == event.category_id
        )
        result = await self._session.execute(stmt)
        stat = result.scalar_one_or_none()
        
        if stat:
            stat.current_balance = float(event.new_balance)
            stat.updated_at = event.occurred_at
            await self._session.commit()
    
    async def _update_user_balance(self, user_id: str, tx_type: str, amount: Decimal):
        """Обновление баланса пользователя"""
        
        stmt = select(UserBalanceViewModel).where(
            UserBalanceViewModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        balance = result.scalar_one_or_none()
        
        if balance:
            if tx_type == "INCOME":
                balance.total_income += float(amount)
            else:
                balance.total_expense += float(amount)
            
            balance.balance = balance.total_income - balance.total_expense
            balance.transaction_count += 1
            balance.last_transaction_at = datetime.now()
            balance.updated_at = datetime.now()
        else:
            # Создаём новый баланс
            new_balance = UserBalanceViewModel(
                user_id=user_id,
                total_income=float(amount) if tx_type == "INCOME" else 0,
                total_expense=float(amount) if tx_type == "EXPENSE" else 0,
                balance=float(amount) if tx_type == "INCOME" else -float(amount),
                transaction_count=1,
                last_transaction_at=datetime.now()
            )
            self._session.add(new_balance)
        
        await self._session.commit()
    
    async def _update_category_statistics(
        self, 
        user_id: str, 
        category_id: str, 
        tx_type: str, 
        amount: Decimal
    ):
        """Обновление статистики по категории"""
        
        # Получаем название категории из Write Model
        from infrastructure.adapter.out.models import CategoryModel
        cat_result = await self._session.execute(
            select(CategoryModel).where(CategoryModel.category_id == category_id)
        )
        category = cat_result.scalar_one_or_none()
        
        stmt = select(CategoryStatisticsViewModel).where(
            CategoryStatisticsViewModel.user_id == user_id,
            CategoryStatisticsViewModel.category_id == category_id
        )
        result = await self._session.execute(stmt)
        stat = result.scalar_one_or_none()
        
        if stat:
            if tx_type == "INCOME":
                stat.total_income += float(amount)
            else:
                stat.total_expense += float(amount)
            
            stat.current_balance = stat.total_income - stat.total_expense
            stat.transaction_count += 1
            stat.last_transaction_at = datetime.now()
            stat.updated_at = datetime.now()
            
            # Расчёт процента использования бюджета
            if stat.budget_percentage > 0:
                expected_budget = (stat.total_income * stat.budget_percentage / 100) if stat.total_income > 0 else 0
                stat.budget_used_percentage = (stat.total_expense / expected_budget * 100) if expected_budget > 0 else 0
        else:
            new_stat = CategoryStatisticsViewModel(
                user_id=user_id,
                category_id=category_id,
                category_name=category.name if category else category_id,
                total_income=float(amount) if tx_type == "INCOME" else 0,
                total_expense=float(amount) if tx_type == "EXPENSE" else 0,
                current_balance=float(amount) if tx_type == "INCOME" else -float(amount),
                budget_percentage=float(category.budget_percentage) if category else 0,
                transaction_count=1,
                last_transaction_at=datetime.now()
            )
            self._session.add(new_stat)
        
        await self._session.commit()


# Регистрация обработчиков событий
class EventHandlersRegistry:
    """Регистрация обработчиков для доменных событий"""
    
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._handlers = {}
    
    def register(self, event_type, handler_method):
        """Регистрация обработчика"""
        self._handlers[event_type] = handler_method
    
    async def handle(self, event):
        """Обработка события"""
        event_type = type(event).__name__
        if event_type in self._handlers:
            async with self._session_factory() as session:
                projection = TransactionProjection(session)
                handler = getattr(projection, self._handlers[event_type])
                await handler(event)


# Настройка регистрации
registry = EventHandlersRegistry(AsyncSessionLocal)
registry.register("TransactionCreatedEvent", "on_transaction_created")
registry.register("TransactionCompletedEvent", "on_transaction_completed")
registry.register("BalanceUpdatedEvent", "on_balance_updated")