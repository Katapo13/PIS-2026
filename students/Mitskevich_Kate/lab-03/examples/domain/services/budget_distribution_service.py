class BudgetDistributionService:
    """Domain Service: распределение дохода по категориям"""
    
    def distribute_income(self, total_amount: Decimal, 
                          categories: List[Category]) -> List[CategoryDistribution]:
        distributions = []
        for cat in categories:
            amount = total_amount * cat.budget_percentage / 100
            if amount > 0:
                distributions.append(
                    CategoryDistribution(cat.category_id, amount, cat.budget_percentage)
                )
        return distributions