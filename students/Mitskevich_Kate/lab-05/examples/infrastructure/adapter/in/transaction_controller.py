from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

from application.service.transaction_application_service import TransactionApplicationService
from application.command.create_income_command import CreateIncomeCommand
from application.command.create_expense_command import CreateExpenseCommand
from application.query.get_transaction_by_id_query import GetTransactionByIdQuery
from application.query.list_user_transactions_query import ListUserTransactionsQuery
from application.query.dto.transaction_dto import TransactionTypeDto

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# Request DTOs
class CreateIncomeRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    idempotency_key: str
    source: Optional[str] = None


class CreateExpenseRequest(BaseModel):
    user_id: str = Field(..., min_length=3)
    category_id: str
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    idempotency_key: str
    allow_negative: bool = False


class TransactionResponse(BaseModel):
    transaction_id: str
    user_id: str
    type: str
    amount: float
    description: str
    status: str
    created_at: datetime
    category_distributions: List[dict]


# Endpoints
@router.post("/income", response_model=dict)
async def create_income(
    request: CreateIncomeRequest,
    service: TransactionApplicationService = Depends(get_transaction_service)
):
    """Зарегистрировать доход"""
    command = CreateIncomeCommand(
        user_id=request.user_id,
        amount=request.amount,
        description=request.description,
        idempotency_key=request.idempotency_key,
        source=request.source
    )
    transaction_id = await service.create_income(command)
    return {"transaction_id": transaction_id, "status": "success"}


@router.post("/expense", response_model=dict)
async def create_expense(
    request: CreateExpenseRequest,
    service: TransactionApplicationService = Depends(get_transaction_service)
):
    """Зарегистрировать расход"""
    command = CreateExpenseCommand(
        user_id=request.user_id,
        category_id=request.category_id,
        amount=request.amount,
        description=request.description,
        idempotency_key=request.idempotency_key,
        allow_negative=request.allow_negative
    )
    transaction_id = await service.create_expense(command)
    return {"transaction_id": transaction_id, "status": "success"}


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    service: TransactionApplicationService = Depends(get_transaction_service)
):
    """Получить транзакцию по ID"""
    query = GetTransactionByIdQuery(transaction_id=transaction_id)
    result = await service.get_transaction_by_id(query)
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result


@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    user_id: str = Query(..., min_length=3),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    transaction_type: Optional[TransactionTypeDto] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    service: TransactionApplicationService = Depends(get_transaction_service)
):
    """Список транзакций пользователя"""
    query = ListUserTransactionsQuery(
        user_id=user_id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type,
        from_date=from_date,
        to_date=to_date
    )
    return await service.list_user_transactions(query)


@router.get("/users/{user_id}/balance")
async def get_balance(
    user_id: str,
    service: TransactionApplicationService = Depends(get_transaction_service)
):
    """Получить баланс пользователя по категориям"""
    from application.query.get_user_balance_query import GetUserBalanceQuery
    query = GetUserBalanceQuery(user_id=user_id)
    return await service.get_user_balance(query)