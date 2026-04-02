class TransactionService(CreateIncomeUseCase, CreateExpenseUseCase):
    """Application Service реализует use-case"""
    
    def __init__(
        self,
        transaction_repo: TransactionRepository,      # Интерфейс!
        category_repo: CategoryRepository,           # Интерфейс!
        budget_repo: BudgetSettingsRepository        # Интерфейс!
    ):
        self._transaction_repo = transaction_repo
        self._category_repo = category_repo
        self._budget_repo = budget_repo