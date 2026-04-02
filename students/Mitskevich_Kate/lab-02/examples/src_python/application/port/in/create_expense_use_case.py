class CreateExpenseUseCase(ABC):
    """Входящий порт для регистрации расхода"""
    
    @abstractmethod
    def create_expense(self, command: CreateExpenseCommand) -> str:
        """
        Зарегистрировать расход из указанной категории
        
        Returns:
            ID созданной транзакции
        """
        pass

@dataclass
class CreateExpenseCommand:
    """Команда для регистрации расхода"""
    user_id: str
    category_id: str
    amount: Decimal
    description: Optional[str]
    idempotency_key: str
    allow_negative: bool = False   # Разрешить уход в минус

    def create_expense(self, command: CreateExpenseCommand) -> str:
    # Проверка идемпотентности
    existing = self._transaction_repo.find_by_idempotency_key(
        command.idempotency_key
    )
    if existing:
        return existing.id
    
    # Получение категории с блокировкой
    category = self._category_repo.find_by_id_with_lock(command.category_id)
    
    if category.balance < command.amount and not command.allow_negative:
        raise InsufficientFundsError(
            f"Недостаточно средств в категории {category.name}. "
            f"Доступно: {category.balance}, требуется: {command.amount}"
        )
    
    # Создание и сохранение транзакции
    transaction = Transaction.create_expense(
        user_id=command.user_id,
        category_id=command.category_id,
        amount=command.amount,
        description=command.description
    )
    
    with self._transaction_repo.begin_transaction():
        self._transaction_repo.save(transaction)
        self._category_repo.update_balance(
            command.category_id,
            category.balance - command.amount
        )
    
    return transaction.id