from fastapi import FastAPI, Depends
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.event_bus.rabbitmq_publisher import RabbitMQPublisher
from infrastructure.config.database import get_session

app = FastAPI(title="Transaction Service", port=8001)
publisher = RabbitMQPublisher()


@app.post("/api/transactions/income")
async def create_income(
    user_id: str,
    amount: Decimal,
    description: str,
    idempotency_key: str,
    session: AsyncSession = Depends(get_session)
):
    # Создание транзакции
    transaction = await create_income_transaction(
        user_id, amount, description, idempotency_key, session
    )
    
    # Публикация события
    await publisher.publish("TransactionCreated", {
        "transaction_id": transaction.id,
        "user_id": user_id,
        "amount": float(amount),
        "type": "INCOME",
        "created_at": transaction.created_at.isoformat()
    })
    
    return {"transaction_id": transaction.id, "status": "success"}


@app.get("/api/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    session: AsyncSession = Depends(get_session)
):
    return await find_transaction_by_id(transaction_id, session)