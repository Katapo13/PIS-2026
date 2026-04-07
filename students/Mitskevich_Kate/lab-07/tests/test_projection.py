import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from cqrs.projection.transaction_projection import TransactionProjection
from domain.events.transaction_events import TransactionCreatedEvent, BalanceUpdatedEvent


class TestTransactionProjection:
    
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def projection(self, mock_session):
        return TransactionProjection(mock_session)
    
    @pytest.mark.asyncio
    async def test_on_transaction_created_creates_view(self, projection, mock_session):
        # Arrange
        event = TransactionCreatedEvent(
            transaction_id="TXN-2026-00001",
            user_id="user-001",
            transaction_type="INCOME",
            amount=Decimal("1000"),
            description="Зарплата",
            category_distributions=[
                {"category_id": "CAT-001", "amount": 600},
                {"category_id": "CAT-002", "amount": 400}
            ]
        )
        
        # Act
        await projection.on_transaction_created(event)
        
        # Assert
        assert mock_session.add.called
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_on_balance_updated_updates_statistics(self, projection, mock_session):
        # Arrange
        event = BalanceUpdatedEvent(
            category_id="CAT-001",
            user_id="user-001",
            old_balance=Decimal("500"),
            new_balance=Decimal("700"),
            change_amount=Decimal("200")
        )
        
        # Mock существующей статистики
        mock_stat = Mock()
        mock_stat.current_balance = 500.0
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_stat
        mock_session.execute.return_value = mock_result
        
        # Act
        await projection.on_balance_updated(event)
        
        # Assert
        assert mock_stat.current_balance == 700.0
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_update_user_balance_creates_new(self, projection, mock_session):
        # Arrange
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Act
        await projection._update_user_balance("user-new", "INCOME", Decimal("500"))
        
        # Assert
        assert mock_session.add.called
        new_balance = mock_session.add.call_args[0][0]
        assert new_balance.user_id == "user-new"
        assert new_balance.total_income == 500.0