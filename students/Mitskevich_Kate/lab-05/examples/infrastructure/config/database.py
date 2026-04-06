# infrastructure/config/database.py
"""
Database Configuration: SQLAlchemy Session Management

Предметная область: Финучёт «Где мои деньги»
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import contextmanager, asynccontextmanager
import os
from typing import Generator, AsyncGenerator

# ============================================
# 1. Синхронная конфигурация (для миграций и тестов)
# ============================================

# Database URL из переменной окружения (синхронный)
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/money_db"
)

# Engine: Connection Pool (синхронный)
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False  # Логирование SQL запросов (True для отладки)
)

# SessionLocal: Factory для создания сессий (синхронный)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)


def get_sync_session() -> Generator[Session, None, None]:
    """
    Dependency Injection для синхронных операций (миграции, скрипты)
    
    Использование:
        with get_sync_session() as session:
            repo = CategoryRepository(session)
            category = repo.find_by_id("CAT-001")
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def sync_session_scope():
    """
    Context Manager для ручного управления синхронными транзакциями
    
    Использование:
        with sync_session_scope() as session:
            repo = TransactionRepository(session)
            repo.save(transaction)
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================
# 2. Асинхронная конфигурация (для FastAPI)
# ============================================

# Database URL из переменной окружения (асинхронный)
ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/money_db"
)

# Async Engine: Connection Pool (асинхронный)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False,  # Логирование SQL запросов (True для отладки)
    pool_timeout=30  # Таймаут получения соединения из пула
)

# AsyncSessionLocal: Factory для создания асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection для FastAPI (асинхронный)
    
    Использование:
        @app.get("/transactions/{id}")
        async def get_transaction(id: str, db: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def async_session_scope():
    """
    Async Context Manager для ручного управления асинхронными транзакциями
    
    Использование:
        async with async_session_scope() as session:
            repo = TransactionRepository(session)
            await repo.save(transaction)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================
# 3. Функции для работы с БД (утилиты)
# ============================================

def init_sync_db():
    """
    Инициализация синхронной БД (создание таблиц)
    Используется для миграций и тестов
    """
    from infrastructure.adapter.out.models import Base
    Base.metadata.create_all(bind=sync_engine)


async def init_async_db():
    """
    Инициализация асинхронной БД (создание таблиц)
    Используется при старте приложения
    """
    from infrastructure.adapter.out.models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_async_db():
    """
    Удаление всех таблиц (для тестов)
    """
    from infrastructure.adapter.out.models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_async_db():
    """
    Закрытие соединения с БД (при остановке приложения)
    """
    await async_engine.dispose()


def close_sync_db():
    """
    Закрытие синхронного соединения с БД
    """
    sync_engine.dispose()


# ============================================
# 4. Проверка подключения к БД
# ============================================

def check_sync_connection() -> bool:
    """
    Проверка синхронного подключения к БД
    
    Returns:
        True если подключение успешно, иначе False
    """
    try:
        with sync_engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def check_async_connection() -> bool:
    """
    Проверка асинхронного подключения к БД
    
    Returns:
        True если подключение успешно, иначе False
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# ============================================
# 5. Получение информации о БД
# ============================================

def get_db_info() -> dict:
    """
    Получение информации о подключении к БД
    """
    return {
        "database_url": SYNC_DATABASE_URL.replace(
            os.getenv("POSTGRES_PASSWORD", "***"), "***"
        ) if os.getenv("POSTGRES_PASSWORD") else SYNC_DATABASE_URL,
        "pool_size": sync_engine.pool.size(),
        "connected": check_sync_connection(),
        "async_enabled": True
    }


# ============================================
# 6. Экспортируемые объекты (для удобства импорта)
# ============================================

__all__ = [
    # Синхронные
    "sync_engine",
    "SyncSessionLocal",
    "get_sync_session",
    "sync_session_scope",
    "init_sync_db",
    "close_sync_db",
    "check_sync_connection",
    # Асинхронные
    "async_engine",
    "AsyncSessionLocal",
    "get_async_session",
    "async_session_scope",
    "init_async_db",
    "drop_async_db",
    "close_async_db",
    "check_async_connection",
    # Утилиты
    "get_db_info",
]