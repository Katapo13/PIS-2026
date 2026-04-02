@dataclass(frozen=True)
class BudgetSetting:
    category_id: str
    percentage: Decimal          # 0-100
    user_id: str