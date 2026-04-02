class Transaction:
    id: str                      # TXN-YYYY-XXXXX
    type: TransactionType        # INCOME или EXPENSE
    amount: Decimal              # Сумма (> 0)
    user_id: str                 # ID пользователя
    description: Optional[str]   # Комментарий
    category_distributions: List[CategoryDistribution]  # Распределение по категориям
    status: TransactionStatus    # PENDING, COMPLETED, FAILED
    idempotency_key: str         # Для предотвращения дублирования
    created_at: datetime
    updated_at: datetime