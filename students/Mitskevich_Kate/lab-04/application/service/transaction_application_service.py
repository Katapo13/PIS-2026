from typing import List, Dict, Optional
from decimal import Decimal

from application.command.create_income_command import CreateIncomeCommand
from application.command.create_expense_command import CreateExpenseCommand
from application.command.update_category_budget_command import UpdateCategoryBudgetCommand
from application.command.handlers.create_income_handler import CreateIncomeHandler
from application.command.handlers.create_expense_handler import CreateExpenseHandler
from application.command.handlers.update_category_budget_handler import UpdateCategoryBudgetHandler

from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.list_user_transactions_query import ListUserTransactionsQuery
from application.query.get_user_balance_query import GetUserBalanceQuery
from application.query.handlers.get_transaction_by_id_handler import GetTransactionByIdHandler
from application.query.handlers.list_user_transactions_handler import ListUserTransactionsHandler
from application.query.handlers.get_user_balance_handler import GetUserBalanceHandler
from application.query.dto.transaction_dto import TransactionDto

class TransactionApplicationService:
    """
    Application Service - фасад для команд и запросов
    Делегирует выполнение специализированным обработчикам
    """
    
    def __init__(
        self,
        # Command Handlers
        create_income_handler: CreateIncomeHandler,
        create_expense_handler: CreateExpenseHandler,
        update_budget_handler: UpdateCategoryBudgetHandler,
        # Query Handlers
        get_transaction_handler: GetTransactionByIdHandler,
        list_transactions_handler: ListUserTransactionsHandler,
        get_balance_handler: GetUserBalanceHandler
    ):
        self._create_income_handler = create_income_handler
        self._create_expense_handler = create_expense_handler
        self._update_budget_handler = update_budget_handler
        self._get_transaction_handler = get_transaction_handler
        self._list_transactions_handler = list_transactions_handler
        self._get_balance_handler = get_balance_handler
    
    # ===== Commands =====
    
    def create_income(self, command: CreateIncomeCommand) -> str:
        """Зарегистрировать доход"""
        return self._create_income_handler.handle(command)
    
    def create_expense(self, command: CreateExpenseCommand) -> str:
        """Зарегистрировать расход"""
        return self._create_expense_handler.handle(command)
    
    def update_category_budget(self, command: UpdateCategoryBudgetCommand) -> None:
        """Обновить процент бюджета категории"""
        self._update_budget_handler.handle(command)
    
    # ===== Queries =====
    
    def get_transaction_by_id(self, query: GetTransactionByIdQuery) -> Optional[TransactionDto]:
        """Получить транзакцию по ID"""
        return self._get_transaction_handler.handle(query)
    
    def list_user_transactions(self, query: ListUserTransactionsQuery) -> List[TransactionDto]:
        """Получить список транзакций пользователя"""
        return self._list_transactions_handler.handle(query)
    
    def get_user_balance(self, query: GetUserBalanceQuery) -> Dict[str, Decimal]:
        """Получить баланс пользователя по категориям"""
        return self._get_balance_handler.handle(query)