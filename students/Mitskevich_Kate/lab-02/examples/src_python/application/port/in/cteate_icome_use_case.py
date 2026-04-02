class CreateIncomeUseCase(ABC):
    """Входящий порт для регистрации дохода"""
    
    @abstractmethod
    def create_income(self, command: CreateIncomeCommand) -> str:
        """
        Зарегистрировать доход и распределить по категориям
        
        Returns:
            ID созданной транзакции
        """
        pass

@dataclass
class CreateIncomeCommand:
    """Команда для регистрации дохода"""
    user_id: str
    amount: Decimal
    description: Optional[str]
    idempotency_key: str
    source: Optional[str]        # "Зарплата", "Фриланс" и т.д.

    def create_income(self, command: CreateIncomeCommand) -> str:
    # Проверка идемпотентности
    existing = self._transaction_repo.find_by_idempotency_key(
        command.idempotency_key
    )
    if existing:
        return existing.id
    
    # Получение данных
    budget_settings = self._budget_repo.find_by_user_id(command.user_id)
    
    # Бизнес-логика
    transaction = Transaction.create_income(
        user_id=command.user_id,
        amount=command.amount,
        description=command.description,
        budget_settings=budget_settings
    )
    
    # Атомарное сохранение (в одной БД-транзакции)
    with self._transaction_repo.begin_transaction():
        self._transaction_repo.save(transaction)
        for dist in transaction.category_distributions:
            self._category_repo.update_balance(
                dist.category_id,
                dist.amount
            )
    
    return transaction.id