from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

@dataclass
class BudgetSettings:
    """Entity: настройки бюджета пользователя"""
    user_id: str
    category_percentages: Dict[str, Decimal] = field(default_factory=dict)
    updated_at: datetime = None
    
    def __post_init__(self):
        if not self.user_id:
            raise ValueError("User ID обязателен")
        
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        # Валидация суммы процентов
        if self.category_percentages:
            self._validate_total_percentage()
    
    def _validate_total_percentage(self):
        """Проверка: сумма процентов = 100%"""
        total = sum(self.category_percentages.values())
        if abs(total - Decimal('100')) > Decimal('0.01'):
            raise ValueError(f"Сумма процентов ({total}) должна равняться 100%")
    
    def set_percentage(self, category_id: str, percentage: Decimal):
        """Установить процент для категории"""
        if not 0 <= percentage <= 100:
            raise ValueError("Процент должен быть от 0 до 100")
        
        self.category_percentages[category_id] = percentage
        self._validate_total_percentage()
        self.updated_at = datetime.now()
    
    def get_percentage(self, category_id: str) -> Decimal:
        """Получить процент для категории"""
        return self.category_percentages.get(category_id, Decimal('0'))
    
    def get_categories(self) -> List[str]:
        """Получить список всех категорий с бюджетом"""
        return list(self.category_percentages.keys())
    
    def __eq__(self, other):
        if not isinstance(other, BudgetSettings):
            return False
        return self.user_id == other.user_id