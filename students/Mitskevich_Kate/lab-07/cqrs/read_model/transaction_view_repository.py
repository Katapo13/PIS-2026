from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from datetime import datetime

from cqrs.read_model.transaction_view import TransactionView, UserBalanceView, CategoryStatisticsView
from infrastructure.adapter.out.models import TransactionViewModel, UserBalanceViewModel, CategoryStatisticsViewModel


class TransactionViewRepository:
    """Репозиторий для чтения из денормализованных view"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def find_by_id(self, transaction_id: str) -> Optional[TransactionView]:
        """Найти транзакцию по ID (без JOIN'ов!)"""
        
        result = await self._session.execute(
            select(TransactionViewModel).where(
                TransactionViewModel.transaction_id == transaction_id
            )
        )
        model = result.scalar_one_or_none()
        
        if model:
            return TransactionView(
                transaction_id=model.transaction_id,
                user_id=model.user_id,
                transaction_type=model.transaction_type,
                amount=model.amount,
                description=model.description,
                status=model.status,
                created_at=model.created_at,
                category_names=model.category_names,
                total_categories=model.total_categories
            )
        return None
    
    async def list_by_user(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        transaction_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[TransactionView]:
        """Список транзакций пользователя (оптимизированный)"""
        
        query = select(TransactionViewModel).where(
            TransactionViewModel.user_id == user_id
        )
        
        if transaction_type:
            query = query.where(TransactionViewModel.transaction_type == transaction_type)
        if from_date:
            query = query.where(TransactionViewModel.created_at >= from_date)
        if to_date:
            query = query.where(TransactionViewModel.created_at <= to_date)
        
        query = query.order_by(desc(TransactionViewModel.created_at)).offset(offset).limit(limit)
        
        result = await self._session.execute(query)
        models = result.scalars().all()
        
        return [
            TransactionView(
                transaction_id=m.transaction_id,
                user_id=m.user_id,
                transaction_type=m.transaction_type,
                amount=m.amount,
                description=m.description,
                status=m.status,
                created_at=m.created_at,
                category_names=m.category_names,
                total_categories=m.total_categories
            )
            for m in models
        ]
    
    async def get_user_balance(self, user_id: str) -> Optional[UserBalanceView]:
        """Получить баланс пользователя (мгновенно!)"""
        
        result = await self._session.execute(
            select(UserBalanceViewModel).where(
                UserBalanceViewModel.user_id == user_id
            )
        )
        model = result.scalar_one_or_none()
        
        if model:
            return UserBalanceView(
                user_id=model.user_id,
                total_income=model.total_income,
                total_expense=model.total_expense,
                balance=model.balance,
                last_transaction_at=model.last_transaction_at,
                transaction_count=model.transaction_count
            )
        return None
    
    async def get_category_statistics(self, user_id: str) -> List[CategoryStatisticsView]:
        """Получить статистику по всем категориям пользователя"""
        
        result = await self._session.execute(
            select(CategoryStatisticsViewModel).where(
                CategoryStatisticsViewModel.user_id == user_id
            ).order_by(desc(CategoryStatisticsViewModel.total_expense))
        )
        models = result.scalars().all()
        
        return [
            CategoryStatisticsView(
                category_id=m.category_id,
                category_name=m.category_name,
                total_income=m.total_income,
                total_expense=m.total_expense,
                current_balance=m.current_balance,
                budget_percentage=m.budget_percentage,
                transaction_count=m.transaction_count,
                budget_used_percentage=m.budget_used_percentage
            )
            for m in models
        ]
    
    async def get_top_spending_categories(self, user_id: str, limit: int = 5) -> List[CategoryStatisticsView]:
        """Топ категорий по расходам"""
        
        result = await self._session.execute(
            select(CategoryStatisticsViewModel)
            .where(CategoryStatisticsViewModel.user_id == user_id)
            .order_by(desc(CategoryStatisticsViewModel.total_expense))
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [
            CategoryStatisticsView(
                category_id=m.category_id,
                category_name=m.category_name,
                total_income=m.total_income,
                total_expense=m.total_expense,
                current_balance=m.current_balance,
                budget_percentage=m.budget_percentage,
                transaction_count=m.transaction_count,
                budget_used_percentage=m.budget_used_percentage
            )
            for m in models
        ]