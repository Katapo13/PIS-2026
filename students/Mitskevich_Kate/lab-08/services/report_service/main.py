from fastapi import FastAPI
from decimal import Decimal
from sqlalchemy import select, func

app = FastAPI(title="Report Service", port=8003)


@app.get("/api/reports/monthly/{user_id}")
async def get_monthly_report(user_id: str, year: int, month: int):
    """Получить месячный отчёт по доходам и расходам"""
    
    # Запрос к Read Model (денормализованная таблица)
    result = await session.execute(
        select(
            func.sum(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE 0 END).label('total_income'),
            func.sum(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END).label('total_expense'),
            func.count().label('transaction_count')
        ).from_statement(text("""
            SELECT 
                SUM(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as transaction_count
            FROM monthly_report_views
            WHERE user_id = :user_id AND year = :year AND month = :month
        """))
    )
    
    data = result.one()
    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "total_income": data.total_income or 0,
        "total_expense": data.total_expense or 0,
        "balance": (data.total_income or 0) - (data.total_expense or 0),
        "transaction_count": data.transaction_count or 0
    }


@app.get("/api/reports/categories/{user_id}")
async def get_category_statistics(user_id: str):
    """Получить статистику по категориям"""
    
    result = await session.execute(
        select(CategoryStatisticsView).where(
            CategoryStatisticsView.user_id == user_id
        ).order_by(CategoryStatisticsView.total_expense.desc())
    )
    
    categories = result.scalars().all()
    return [
        {
            "category_id": c.category_id,
            "category_name": c.category_name,
            "total_expense": c.total_expense,
            "total_income": c.total_income,
            "current_balance": c.current_balance,
            "budget_usage_percentage": c.budget_used_percentage
        }
        for c in categories
    ]