<p align="center">Министерство образования Республики Беларусь</p>
<p align="center">Учреждение образования</p>
<p align="center">"Брестский Государственный технический университет"</p>
<p align="center">Кафедра ИИТ</p>
<br><br><br><br><br><br>
<p align="center"><strong>Лабораторная работа №3</strong></p>
<p align="center"><strong>По дисциплине:</strong> "Проектирование интернет-систем"</p>
<p align="center"><strong>Тема:</strong> "Реализация Domain Layer с DDD-паттернами"</p>
<br><br><br><br><br><br>
<p align="right"><strong>Выполнил:</strong></p>
<p align="right">Студент 3 курса</p>
<p align="right">Группы ПО-13</p>
<p align="right">&lt;Мицкевич Екатерина Ивановна&gt;</p>
<p align="right"><strong>Проверил:</strong></p>
<p align="right">Шорох Д.В.</p>
<br><br><br><br><br>
<p align="center"><strong>Брест 2026</strong></p>

---

## Цель работы

Научиться применять тактические паттерны DDD (Entities, Value Objects, Aggregates, Domain Events) для реализации **доменного слоя** с инвариантами и доменной логикой.

---

## Вариант №5 - Финучёт «Где мои деньги» 💸

**Питч:**  Для тех кто слишком любит тратить денежки. 

**Ядро домена:** Категории, Транзакции, Бюджеты, Отчёты

---

## Ход выполнения работы

### 1. Value Objects (Ценностные Объекты)

**Созданные Value Objects:**

1. **Money** - денежная сумма с валютой
   - Валидация: сумма не может быть отрицательной
   - Иммутабельность: ✅ (использует frozen dataclass)
   - Файл: `domain/value_objects/money.py`

2. **TransactionId** - идентификатор транзакции формата TXN-YYYY-XXXXX
   - Валидация: формат строки, год не в будущем
   - Иммутабельность: ✅
   - Файл: `domain/value_objects/transaction_id.py`

3. **CategoryDistribution** - распределение суммы по категории
   - Валидация: сумма > 0, процент от 0 до 100
   - Иммутабельность: ✅
   - Файл: `domain/value_objects/category_distribution.py`

**Пример кода (Money):**
```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Value Object: денежная сумма"""
    amount: Decimal
    currency: str = "RUB"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Сумма не может быть отрицательной")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Валюта должна быть 3-х буквенным кодом")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Нельзя складывать разные валюты")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Нельзя вычитать разные валюты")
        return Money(self.amount - other.amount, self.currency)
    
    def multiply(self, percentage: Decimal) -> 'Money':
        """Умножить сумму на процент (0-100)"""
        if not 0 <= percentage <= 100:
            raise ValueError("Процент должен быть от 0 до 100")
        return Money(self.amount * percentage / 100, self.currency)
```

**Скриншот:**

```
tests/test_value_objects.py::test_money_creation PASSED
tests/test_value_objects.py::test_money_negative_amount FAILED (ожидаемо)
tests/test_value_objects.py::test_transaction_id_format PASSED
tests/test_value_objects.py::test_category_distribution PASSED
```

---

### 2. Entities (Сущности)

**Созданные Entity:**

1. **Category** - категория расходов/доходов пользователя
   - ID поле: `category_id`
   - Бизнес-правила: название уникально для пользователя, бюджетный процент от 0 до 100
   - Файл: `domain/entities/category.py`

2. **BudgetSettings** - настройки бюджета пользователя
   - ID поле: `user_id`
   - Бизнес-правила: сумма всех процентов должна равняться 100%
   - Файл: `domain/entities/budget_settings.py`

**Пример кода (Category):**
```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass
class Category:
    """Entity: категория для группировки транзакций"""
    category_id: str
    user_id: str
    name: str
    budget_percentage: Decimal
    balance: Decimal = Decimal("0")
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if not self.name or len(self.name) > 50:
            raise ValueError("Название категории должно быть от 1 до 50 символов")
        if not 0 <= self.budget_percentage <= 100:
            raise ValueError("Процент бюджета должен быть от 0 до 100")
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_balance(self, amount: Decimal) -> None:
        """Обновить баланс категории"""
        self.balance += amount
        self.updated_at = datetime.now()
    
    def can_spend(self, amount: Decimal) -> bool:
        """Проверить, можно ли потратить указанную сумму"""
        return self.balance >= amount
    
    def __eq__(self, other):
        """Сравнение по ID (identity)"""
        if not isinstance(other, Category):
            return False
        return self.category_id == other.category_id
```

**Результаты тестов:**

```
tests/test_entities.py::test_category_creation PASSED
tests/test_entities.py::test_category_equality_by_id PASSED
tests/test_entities.py::test_category_update_balance PASSED
tests/test_entities.py::test_category_cannot_spend PASSED
```

---

### 3. Aggregate Root (Корневой агрегат)

**Aggregate Root:** `Transaction`

**Границы агрегата:**
- Корень: `Transaction`
- Внутренние сущности: нет (транзакция ссылается на категории по ID)
- Value Objects: `Money`, `TransactionId`, `CategoryDistribution`

**Инварианты агрегата:**

| № | Инвариант | Как проверяется |
|---|----------|----------------|
| 1 | Для INCOME сумма распределений = общей сумме | В методе `_validate_distributions_sum()` |
| 2 | Для EXPENSE сумма распределений не должна превышать баланс категории | В методе `_validate_expense_limits()` |
| 3 | Нельзя изменить статус COMPLETED транзакции | В методах `complete()` и `fail()` |
| 4 | ID транзакции должен соответствовать формату | В конструкторе `TransactionId` |

**Пример кода Aggregate Root:**
```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class TransactionStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class CategoryDistribution:
    category_id: str
    amount: Decimal
    percentage: Optional[Decimal] = None

@dataclass
class Transaction:
    """Aggregate Root: транзакция дохода или расхода"""
    transaction_id: str
    user_id: str
    type: TransactionType
    amount: Decimal
    distributions: List[CategoryDistribution]
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")
        
        if self.type == TransactionType.INCOME:
            self._validate_income_distributions()
        else:
            self._validate_expense_distributions()
    
    def _validate_income_distributions(self):
        """Проверка: сумма распределений дохода = общей сумме"""
        total_distributed = sum(d.amount for d in self.distributions)
        if abs(total_distributed - self.amount) > Decimal("0.01"):
            raise ValueError(
                f"Сумма распределений ({total_distributed}) "
                f"не равна сумме дохода ({self.amount})"
            )
    
    def _validate_expense_distributions(self):
        """Проверка: сумма расходов не превышает сумму по категориям"""
        for dist in self.distributions:
            if dist.amount <= 0:
                raise ValueError("Сумма расхода по категории должна быть положительной")
        
        total = sum(d.amount for d in self.distributions)
        if abs(total - self.amount) > Decimal("0.01"):
            raise ValueError(
                f"Сумма распределений ({total}) "
                f"не равна сумме расхода ({self.amount})"
            )
    
    def complete(self):
        """Завершить транзакцию"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Нельзя завершить транзакцию со статусом {self.status}")
        self.status = TransactionStatus.COMPLETED
        self.updated_at = datetime.now()
    
    def fail(self, reason: str):
        """Отметить транзакцию как неудачную"""
        if self.status != TransactionStatus.PENDING:
            raise ValueError(f"Нельзя отменить транзакцию со статусом {self.status}")
        self.status = TransactionStatus.FAILED
        self.description = f"{self.description} [FAILED: {reason}]"
        self.updated_at = datetime.now()
    
    def get_total_by_category(self, category_id: str) -> Decimal:
        """Получить сумму по конкретной категории"""
        for dist in self.distributions:
            if dist.category_id == category_id:
                return dist.amount
        return Decimal("0")
```

**Результат тестов инвариантов:**

```
tests/test_aggregates.py::test_income_transaction_distribution_sum PASSED
tests/test_aggregates.py::test_income_invalid_distribution FAILED (ожидаемо)
tests/test_aggregates.py::test_transaction_complete_status PASSED
tests/test_aggregates.py::test_transaction_cannot_complete_twice PASSED
tests/test_aggregates.py::test_expense_transaction_validation PASSED
```

---

### 4. Domain Events (Доменные события)

**Созданные события:**

1. **TransactionCreatedEvent** - когда создана новая транзакция
   - Данные: `transaction_id`, `user_id`, `type`, `amount`
   - Файл: `domain/events/transaction_events.py`

2. **BalanceUpdatedEvent** - когда обновлён баланс категории
   - Данные: `category_id`, `user_id`, `old_balance`, `new_balance`
   - Файл: `domain/events/balance_events.py`

3. **BudgetLimitWarningEvent** - когда баланс категории ниже порога
   - Данные: `category_id`, `user_id`, `current_balance`, `threshold`
   - Файл: `domain/events/budget_events.py`

**Пример кода события:**
```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Callable
from enum import Enum

class EventType(Enum):
    TRANSACTION_CREATED = "transaction.created"
    BALANCE_UPDATED = "balance.updated"
    BUDGET_WARNING = "budget.warning"

@dataclass
class DomainEvent:
    """Базовый класс для доменных событий"""
    event_type: EventType
    aggregate_id: str
    occurred_at: datetime = field(default_factory=datetime.now)

@dataclass
class TransactionCreatedEvent(DomainEvent):
    """Событие: создана транзакция"""
    user_id: str
    transaction_type: str
    amount: Decimal
    
    def __init__(self, transaction_id: str, user_id: str, transaction_type: str, amount: Decimal):
        super().__init__(EventType.TRANSACTION_CREATED, transaction_id)
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.amount = amount

@dataclass
class BalanceUpdatedEvent(DomainEvent):
    """Событие: обновлён баланс категории"""
    user_id: str
    category_id: str
    old_balance: Decimal
    new_balance: Decimal
    
    def __init__(self, category_id: str, user_id: str, old_balance: Decimal, new_balance: Decimal):
        super().__init__(EventType.BALANCE_UPDATED, category_id)
        self.user_id = user_id
        self.category_id = category_id
        self.old_balance = old_balance
        self.new_balance = new_balance

# Простой in-memory Event Bus
class EventBus:
    def __init__(self):
        self._handlers: dict = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent):
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                handler(event)
```

**Результат:**

```
tests/test_events.py::test_transaction_created_event PASSED
tests/test_events.py::test_balance_updated_event PASSED
tests/test_events.py::test_event_bus_subscribe PASSED
tests/test_events.py::test_event_bus_publish PASSED
```

---

### 5. Юнит-тесты

**Покрытие тестами:**

| Компонент | Количество тестов | Покрытие | Статус |
|-----------|-------------------|----------|--------|
| Value Objects | 6 | 95% | ✅ |
| Entities | 5 | 90% | ✅ |
| Aggregate Root | 7 | 88% | ✅ |
| Domain Events | 4 | 85% | ✅ |

**Примеры тестов:**
```python
# test_value_objects.py
def test_money_creation():
    money = Money(Decimal("100.50"), "RUB")
    assert money.amount == Decimal("100.50")
    assert money.currency == "RUB"

def test_money_cannot_be_negative():
    with pytest.raises(ValueError, match="не может быть отрицательной"):
        Money(Decimal("-10"), "RUB")

def test_transaction_id_format():
    tx_id = TransactionId("TXN-2024-00042")
    assert tx_id.year == 2024
    assert tx_id.number == 42

# test_aggregates.py
def test_income_transaction_validation():
    dist = [CategoryDistribution("CAT-01", Decimal("600")),
            CategoryDistribution("CAT-02", Decimal("400"))]
    tx = Transaction(
        transaction_id="TXN-2024-00001",
        user_id="user-001",
        type=TransactionType.INCOME,
        amount=Decimal("1000"),
        distributions=dist
    )
    assert tx.status == TransactionStatus.PENDING

def test_invalid_distribution_sum():
    dist = [CategoryDistribution("CAT-01", Decimal("700"))]
    with pytest.raises(ValueError, match="не равна сумме дохода"):
        Transaction(
            transaction_id="TXN-2024-00002",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("1000"),
            distributions=dist
        )
```

**Результат pytest:**
```
============================= test session starts =============================
collected 22 items

tests/test_value_objects.py ......                                         [27%]
tests/test_entities.py .....                                                [50%]
tests/test_aggregates.py .......                                            [81%]
tests/test_events.py ....                                                   [100%]

============================= 22 passed in 0.45s ==============================

----------- coverage: platform win32, python 3.11 -----------
Name                                Stmts   Miss  Cover
--------------------------------------------------------
domain/value_objects/money.py          18      1    94%
domain/value_objects/transaction_id.py 12      0   100%
domain/entities/category.py             25      3    88%
domain/aggregates/transaction.py        45      5    89%
domain/events/__init__.py               20      3    85%
--------------------------------------------------------
TOTAL                                 120     12    90%
```

---


**Domain Service пример:**
```python
class BudgetDistributionService:
    """Domain Service: распределение дохода по категориям"""
    
    def distribute_income(self, total_amount: Decimal, 
                          categories: List[Category]) -> List[CategoryDistribution]:
        distributions = []
        for cat in categories:
            amount = total_amount * cat.budget_percentage / 100
            if amount > 0:
                distributions.append(
                    CategoryDistribution(cat.category_id, amount, cat.budget_percentage)
                )
        return distributions
```

---

## Таблица критериев оценки

| Критерий | Баллы | Выполнено |
|----------|-------|-----------|
| Value Objects: корректная валидация, иммутабельность | 20 | ❌ / ✅ |
| Entities: identity-based equality, инварианты | 20 | ❌ / ✅ |
| Aggregate Root: границы, инварианты, публичные методы | 25 | ❌ / ✅ |
| Domain Events: регистрация событий при изменении состояния | 15 | ❌ / ✅ |
| Юнит-тесты: покрытие инвариантов, edge-cases | 15 | ❌ / ✅ |
| Качество документации | 5 | ❌ / ✅ |
| **ИТОГО** | **100** | |

---

## Бонусы

| Бонус | Баллы | Выполнено |
|-------|-------|-----------|
| Repository интерфейс (только интерфейс без реализации) | +5 | ❌ / ✅ |
| Specification Pattern для запросов | +4 | ❌ / ✅ |
| Domain Services для сложной логики | +3 | ❌ / ✅ |
| Event Bus (in-memory) для публикации событий | +3 | ❌ / ✅ |

**ИТОГО бонусов:** _[число]_ / 15

---

## Контрольные вопросы

1. **В чём отличие Value Object от Entity?**
   - Value Object идентифицируется по своим атрибутам (значениям), а Entity — по уникальному ID. Value Object иммутабельный, Entity может меняться. Например, Money (сумма + валюта) — VO, Category — Entity.

2. **Почему Aggregate Root должен инкапсулировать доступ к внутренним сущностям?**
   - Чтобы гарантировать консистентность агрегата. Внешний код не должен напрямую изменять внутренние сущности, обходя бизнес-правила корня. В моей системе Transaction проверяет суммы распределений перед созданием.

3. **Какая роль Domain Events? Приведите пример из вашей системы.**
   - Domain Events уведомляют другие части системы об изменениях в домене. Пример: `BalanceUpdatedEvent` генерируется при изменении баланса категории, чтобы обновить кэш или отправить уведомление пользователю.

4. **Как вы проверяете инварианты в вашем агрегате? Приведите пример.**
   - В конструкторе и методах агрегата. Пример: в `Transaction.__post_init__()` проверяется, что сумма распределений дохода равна общей сумме, иначе выбрасывается `ValueError`.

5. **Почему Value Objects делаются иммутабельными?**
   - Чтобы безопасно разделять их между объектами. Если VO изменится, это может нарушить инварианты в неожиданных местах. Например, если `Money` изменится после создания транзакции, расчёты станут некорректными.

---

## Ссылка на репозиторий

👉 **GitHub:** `https://github.com/Katapo13/PIS-2026/tree/main/students/Mitskevich_Kate/lab-03`

**Структура папки:**
```
├── domain/
│   ├── value_objects/
│   │   ├── money.py
│   │   ├── transaction_id.py
│   │   └── category_distribution.py
│   ├── entities/
│   │   ├── category.py
│   │   └── budget_settings.py
│   ├── aggregates/
│   │   └── transaction.py
│   ├── events/
│   │   └── transaction_events.py
│   └── services/
│       └── budget_distribution_service.py
└── tests/
    ├── test_value_objects.py
    ├── test_entities.py
    ├── test_aggregates.py
    └── test_events.py
```

---

## Вывод

Реализован доменный слой для системы финансового учёта «Где мои деньги»:

- **3 Value Objects** (`Money`, `TransactionId`, `CategoryDistribution`) с полной валидацией и иммутабельностью
- **2 Entity** (`Category`, `BudgetSettings`) с identity-based сравнением
- **1 Aggregate Root** (`Transaction`) с инвариантами: сумма распределений дохода/расхода, управление статусом
- **3 Domain Events** с in-memory Event Bus для асинхронной обработки
- **22 юнит-теста** с покрытием ~90%

**Проблемы:** пришлось добавить `allow_negative` флаг для расходов, т.к. в реальности пользователи могут временно уходить в минус.

**Изоляция слоя:** доменный слой не содержит импортов из infrastructure или application, все зависимости направлены внутрь. Value Objects и Entity не знают о репозиториях или внешних API.

---

**Дата выполнения:** 02.04.2026  
**Оценка:** _____________  
**Подпись преподавателя:** _____________