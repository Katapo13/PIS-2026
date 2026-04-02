from dataclasses import dataclass
from datetime import datetime
import re

@dataclass(frozen=True)
class TransactionId:
    """Value Object: идентификатор транзакции формата TXN-YYYY-XXXXX"""
    value: str
    
    def __post_init__(self):
        pattern = r'^TXN-\d{4}-\d{5}$'
        if not re.match(pattern, self.value):
            raise ValueError(f"Неверный формат ID транзакции: {self.value}. Ожидается TXN-YYYY-XXXXX")
        
        year = int(self.value.split('-')[1])
        current_year = datetime.now().year
        if year > current_year:
            raise ValueError(f"Год в ID транзакции ({year}) не может быть в будущем")
    
    @property
    def year(self) -> int:
        return int(self.value.split('-')[1])
    
    @property
    def number(self) -> int:
        return int(self.value.split('-')[2])
    
    @staticmethod
    def generate(user_id: str, timestamp: datetime = None) -> 'TransactionId':
        """Генерация нового ID транзакции"""
        if timestamp is None:
            timestamp = datetime.now()
        year = timestamp.year
        # Упрощённая генерация: хэш от user_id + timestamp
        import hashlib
        hash_input = f"{user_id}{timestamp.timestamp()}".encode()
        number = int(hashlib.md5(hash_input).hexdigest()[:5], 16) % 100000
        return TransactionId(f"TXN-{year}-{number:05d}")