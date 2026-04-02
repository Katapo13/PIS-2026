from typing import List, Optional
from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.dto.transaction_dto import TransactionDto, TransactionTypeDto, TransactionStatusDto
from application.port.out.transaction_repository import TransactionRepository

class GetTransactionByIdHandler:
    """Обработчик запроса получения транзакции по ID"""
    
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo
    
    def handle(self, query: GetTransactionByIdQuery) -> Optional[TransactionDto]:
        """Получить транзакцию по ID"""
        
        transaction = self._transaction_repo.find_by_id(query.transaction_id)
        
        if not transaction:
            return None
        
        return TransactionDto(
            transaction_id=transaction.transaction_id,
            user_id=transaction.user_id,
            type=TransactionTypeDto(transaction.type.value),
            amount=transaction.amount,
            description=transaction.description,
            status=TransactionStatusDto(transaction.status.value),
            created_at=transaction.created_at,
            category_distributions=[
                {"category_id": d.category_id, "amount": d.amount}
                for d in transaction.distributions
            ]
        )

class ListUserTransactionsHandler:
    """Обработчик запроса списка транзакций пользователя"""
    
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo
    
    def handle(self, query) -> List[TransactionDto]:
        """Получить список транзакций пользователя"""
        
        transactions = self._transaction_repo.find_by_user_id(
            query.user_id,
            limit=query.limit,
            offset=query.offset,
            transaction_type=query.transaction_type.value if query.transaction_type else None,
            from_date=query.from_date,
            to_date=query.to_date
        )
        
        return [
            TransactionDto(
                transaction_id=t.transaction_id,
                user_id=t.user_id,
                type=TransactionTypeDto(t.type.value),
                amount=t.amount,
                description=t.description,
                status=TransactionStatusDto(t.status.value),
                created_at=t.created_at,
                category_distributions=[
                    {"category_id": d.category_id, "amount": d.amount}
                    for d in t.distributions
                ]
            )
            for t in transactions
        ]