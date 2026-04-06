from sqlalchemy import Column, String, DateTime, Float, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class TransactionTypeEnum(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TransactionStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TransactionModel(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(Enum(TransactionTypeEnum), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, default="")
    status = Column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING)
    idempotency_key = Column(String, unique=True, index=True)
    category_distributions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CategoryModel(Base):
    __tablename__ = "categories"
    
    category_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    budget_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)