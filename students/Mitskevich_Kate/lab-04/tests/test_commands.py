import pytest
from decimal import Decimal
from application.command.create_income_command import CreateIncomeCommand


class TestCreateIncomeCommand:
    """Тесты для команды CreateIncomeCommand"""
    
    def test_valid_command_creation(self):
        """Тест создания валидной команды"""
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("1000.00"),
            description="Зарплата",
            idempotency_key="key-001",
            source="Зарплата"
        )
        
        assert command.user_id == "user-001"
        assert command.amount == Decimal("1000.00")
        assert command.description == "Зарплата"
        assert command.idempotency_key == "key-001"
        assert command.source == "Зарплата"
    
    def test_command_without_description(self):
        """Тест команды без описания"""
        command = CreateIncomeCommand(
            user_id="user-001",
            amount=Decimal("500.00"),
            idempotency_key="key-002"
        )
        
        assert command.description is None
        assert command.source is None
    
    def test_invalid_user_id_too_short(self):
        """Тест: user_id слишком короткий"""
        with pytest.raises(ValueError, match="user_id должен быть не менее 3 символов"):
            CreateIncomeCommand(
                user_id="a",
                amount=Decimal("100"),
                idempotency_key="key-003"
            )
    
    def test_invalid_amount_zero(self):
        """Тест: сумма равна нулю"""
        with pytest.raises(ValueError, match="Сумма дохода должна быть положительной"):
            CreateIncomeCommand(
                user_id="user-001",
                amount=Decimal("0"),
                idempotency_key="key-004"
            )
    
    def test_invalid_amount_negative(self):
        """Тест: отрицательная сумма"""
        with pytest.raises(ValueError, match="Сумма дохода должна быть положительной"):
            CreateIncomeCommand(
                user_id="user-001",
                amount=Decimal("-100"),
                idempotency_key="key-005"
            )
    
    def test_empty_idempotency_key(self):
        """Тест: пустой ключ идемпотентности"""
        with pytest.raises(ValueError, match="idempotency_key обязателен"):
            CreateIncomeCommand(
                user_id="user-001",
                amount=Decimal("100"),
                idempotency_key=""
            )