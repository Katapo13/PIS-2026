class Category:
    id: str
    name: str                    # "Покушать", "Накопления"
    user_id: str
    balance: Decimal             # Текущий баланс
    budget_percentage: Decimal   # Процент от дохода (0-100)
    created_at: datetime
    updated_at: datetime