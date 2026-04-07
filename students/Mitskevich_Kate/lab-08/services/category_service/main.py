from fastapi import FastAPI, Depends
from decimal import Decimal

app = FastAPI(title="Category Service", port=8002)


@app.post("/api/categories")
async def create_category(user_id: str, name: str, budget_percentage: Decimal):
    category = Category(
        category_id=f"CAT-{uuid4().hex[:8]}",
        user_id=user_id,
        name=name,
        budget_percentage=budget_percentage
    )
    await save_category(category)
    
    # Публикация события
    await publisher.publish("CategoryCreated", {
        "category_id": category.category_id,
        "user_id": user_id,
        "name": name,
        "budget_percentage": float(budget_percentage)
    })
    
    return {"category_id": category.category_id}


@app.put("/api/categories/{category_id}/budget")
async def update_budget(category_id: str, percentage: Decimal):
    category = await find_category(category_id)
    category.update_budget(percentage)
    await save_category(category)
    
    # Публикация события
    await publisher.publish("BudgetUpdated", {
        "category_id": category_id,
        "user_id": category.user_id,
        "new_percentage": float(percentage)
    })
    
    return {"status": "updated"}