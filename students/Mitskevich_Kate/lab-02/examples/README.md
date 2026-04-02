# Лабораторная работа №2
## Реализация Request Service для системы «Где мои деньги» 💸
### Гексагональная архитектура

---

## 📋 Описание

Данный пример демонстрирует реализацию **Transaction Service** (Сервис управления транзакциями) с использованием гексагональной архитектуры для системы финансового учёта «Где мои деньги».

**Transaction Service** отвечает за:
- Регистрацию доходов и расходов
- Автоматическое распределение доходов по категориям согласно настройкам бюджета
- Обновление балансов категорий
- Обеспечение атомарности операций
- Идемпотентную обработку запросов

---

## Архитектура

### Слои системы

```
┌─────────────────────────────────────────────────────────────┐
│   Infrastructure Layer                                      │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────┐ │
│  │   REST      │    │   PostgreSQL     │    │   Redis    │ │
│  │ Controller  │    │   Repository     │    │  Cache     │ │
│  │   (HTTP)    │    │   (Adapter)      │    │  Adapter   │ │
│  └──────┬──────┘    └────────┬─────────┘    └─────┬──────┘ │
│         │                    │                    │        │
│         │     ┌──────────────┴──────────────────┐ │        │
│         │     │  Message Queue (Outbox)        │ │        │
│         │     │  (Async Event Publisher)       │ │        │
│         │     └─────────────────────────────────┘ │        │
└─────────┼────────────────────┬────────────────────┼────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│   Application Layer                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Ports (Interfaces)                          │   │
│  │  ┌────────────────┐      ┌──────────────────────┐   │   │
│  │  │   Inbound      │      │    Outbound          │   │   │
│  │  │   Ports        │      │    Ports             │   │   │
│  │  │                │      │                      │   │   │
│  │  │ • CreateIncome │      │ • TransactionRepo    │   │   │
│  │  │ • CreateExpense│      │ • CategoryRepo       │   │   │
│  │  └────────┬───────┘      │ • BudgetSettingsRepo │   │   │
│  └───────────┼──────────────────┼──────────────────┘   │   │
│              │                  │                      │   │
│  ┌───────────▼──────────────────▼────────────────────┐  │   │
│  │           TransactionService                      │  │   │
│  │  (implements CreateIncomeUseCase,                 │  │   │
│  │   CreateExpenseUseCase)                           │  │   │
│  └───────────────────────────────────────────────────┘  │   │
└─────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│       Domain Layer                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Transaction  │  │   Category   │  │ BudgetSetting│      │
│  │ (Aggregate)  │  │  (Entity)    │  │  (ValueObj)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                            │
│  Business Rules:                                           │
│  - Transaction ID: TXN-YYYY-XXXXX                          │
│  - Amount > 0 for INCOME, < 0 for EXPENSE                  │
│  - Income distribution sum must equal total amount         │
│  - Category balance cannot go below 0 (optional warning)   │
│  - Budget percentages must sum to 100%                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Структура проекта

```
lab-02/
├── README.md                      # Основная документация
├── architecture-diagram.puml      # PlantUML диаграмма слоёв
└── src_python/                    # Python реализация
    ├── domain/                    # Domain Layer
    │   ├── transaction.py         # Агрегат Transaction
    │   ├── category.py            # Entity Category
    │   ├── budget_setting.py      # Value Object BudgetSetting
    │   └── transaction_status.py  # Enum статусов
    ├── application/               # Application Layer
    │   ├── port/
    │   │   ├── in/
    │   │   │   ├── create_income_use_case.py
    │   │   │   └── create_expense_use_case.py
    │   │   └── out/
    │   │       ├── transaction_repository.py
    │   │       ├── category_repository.py
    │   │       └── budget_settings_repository.py
    │   └── service/
    │       └── transaction_service.py
    ├── infrastructure/            # Infrastructure Layer
    │   ├── adapter/
    │   │   ├── in/
    │   │   │   └── transaction_controller.py  # FastAPI
    │   │   └── out/
    │   │       ├── postgres_transaction_repository.py
    │   │       ├── postgres_category_repository.py
    │   │       ├── postgres_budget_repository.py
    │   │       └── redis_cache_adapter.py
    │   └── config/
    │       └── dependency_injection.py
    ├── main.py                    # FastAPI приложение
    ├── example_cli.py             # CLI пример
    ├── requirements.txt           # Зависимости
    └── README.md                  # Детальная документация
```

---

## 🎯 Основные сущности (из Lab #1)

### 1. Transaction (Транзакция) - Aggregate Root

**Идентификатор:** `TXN-2024-0042`

**Атрибуты:**
```python
class Transaction:
    id: str                      # TXN-YYYY-XXXXX
    type: TransactionType        # INCOME или EXPENSE
    amount: Decimal              # Сумма (> 0)
    user_id: str                 # ID пользователя
    description: Optional[str]   # Комментарий
    category_distributions: List[CategoryDistribution]  # Распределение по категориям
    status: TransactionStatus    # PENDING, COMPLETED, FAILED
    idempotency_key: str         # Для предотвращения дублирования
    created_at: datetime
    updated_at: datetime
```

**Бизнес-правила:**
- Для INCOME: сумма распределения по категориям = total amount
- Для EXPENSE: сумма списания не может превышать баланс категории (с предупреждением)
- Статус: PENDING → COMPLETED/FAILED
- Одна транзакция может затрагивать несколько категорий

### 2. Category (Категория) - Entity

**Идентификатор:** `CAT-01`

**Атрибуты:**
```python
class Category:
    id: str
    name: str                    # "Покушать", "Накопления"
    user_id: str
    balance: Decimal             # Текущий баланс
    budget_percentage: Decimal   # Процент от дохода (0-100)
    created_at: datetime
    updated_at: datetime
```

**Бизнес-правила:**
- Название категории уникально для пользователя
- Сумма `budget_percentage` для всех категорий пользователя = 100%
- Баланс может быть отрицательным (с предупреждением)

### 3. BudgetSetting (Настройка бюджета) - Value Object

**Атрибуты:**
```python
@dataclass(frozen=True)
class BudgetSetting:
    category_id: str
    percentage: Decimal          # 0-100
    user_id: str
```

**Свойства:**
- Immutable (неизменяемый)
- Equality by value (сравнение по значению)
- Валидация при создании: 0 <= percentage <= 100

---

## 🔌 Порты и адаптеры

### Входящие порты (Inbound Ports)

#### CreateIncomeUseCase

Интерфейс для регистрации дохода:

```python
class CreateIncomeUseCase(ABC):
    """Входящий порт для регистрации дохода"""
    
    @abstractmethod
    def create_income(self, command: CreateIncomeCommand) -> str:
        """
        Зарегистрировать доход и распределить по категориям
        
        Returns:
            ID созданной транзакции
        """
        pass
```

**Command DTO:**
```python
@dataclass
class CreateIncomeCommand:
    """Команда для регистрации дохода"""
    user_id: str
    amount: Decimal
    description: Optional[str]
    idempotency_key: str
    source: Optional[str]        # "Зарплата", "Фриланс" и т.д.
```

#### CreateExpenseUseCase

Интерфейс для регистрации расхода:

```python
class CreateExpenseUseCase(ABC):
    """Входящий порт для регистрации расхода"""
    
    @abstractmethod
    def create_expense(self, command: CreateExpenseCommand) -> str:
        """
        Зарегистрировать расход из указанной категории
        
        Returns:
            ID созданной транзакции
        """
        pass
```

**Command DTO:**
```python
@dataclass
class CreateExpenseCommand:
    """Команда для регистрации расхода"""
    user_id: str
    category_id: str
    amount: Decimal
    description: Optional[str]
    idempotency_key: str
    allow_negative: bool = False   # Разрешить уход в минус
```

### Исходящие порты (Outbound Ports)

#### TransactionRepository

Интерфейс для работы с хранилищем транзакций:

```python
class TransactionRepository(ABC):
    """Исходящий порт для работы с транзакциями"""
    
    @abstractmethod
    def save(self, transaction: Transaction) -> None:
        """Сохранить транзакцию"""
        pass
    
    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Найти транзакцию по ID"""
        pass
    
    @abstractmethod
    def find_by_idempotency_key(self, key: str) -> Optional[Transaction]:
        """Найти транзакцию по ключу идемпотентности"""
        pass
```

#### CategoryRepository

Интерфейс для работы с категориями:

```python
class CategoryRepository(ABC):
    """Исходящий порт для работы с категориями"""
    
    @abstractmethod
    def find_by_id(self, category_id: str) -> Optional[Category]:
        """Найти категорию по ID"""
        pass
    
    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[Category]:
        """Найти все категории пользователя"""
        pass
    
    @abstractmethod
    def update_balance(self, category_id: str, new_balance: Decimal) -> None:
        """Обновить баланс категории (с блокировкой)"""
        pass
```

#### BudgetSettingsRepository

Интерфейс для работы с настройками бюджета:

```python
class BudgetSettingsRepository(ABC):
    """Исходящий порт для работы с настройками бюджета"""
    
    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[BudgetSetting]:
        """Найти настройки бюджета пользователя"""
        pass
    
    @abstractmethod
    def validate_percentage_sum(self, user_id: str) -> bool:
        """Проверить, что сумма процентов = 100%"""
        pass
```

---

## Сценарий работы (Use Case из Lab #1)

### Основной поток: Регистрация дохода

**Сценарий:** Пользователь получает зарплату 1000 руб., система автоматически распределяет 60% на «Покушать» и 40% на «Накопления»

**Шаги:**

1. **Пользователь** отправляет запрос через REST API:
   ```bash
   POST /api/transactions/income
   {
     "userId": "user-001",
     "amount": 1000.00,
     "description": "Зарплата за октябрь",
     "idempotencyKey": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```

2. **TransactionController** (входящий адаптер) получает запрос и вызывает `CreateIncomeUseCase`

3. **TransactionService** (Application Layer):
   - Проверяет идемпотентность через `TransactionRepository`
   - Получает настройки бюджета через `BudgetSettingsRepository`
   - Рассчитывает распределение по категориям
   - Создаёт агрегат `Transaction` (Domain Layer)
   - Открывает БД-транзакцию
   - Сохраняет транзакцию через `TransactionRepository`
   - Обновляет балансы категорий через `CategoryRepository`
   - Commit транзакции
   - Возвращает ID созданной транзакции

4. **Пользователь** получает ответ:
   ```json
   {
     "transactionId": "TXN-2024-0042",
     "status": "COMPLETED",
     "distributions": [
       {"category": "Покушать", "amount": 600.00},
       {"category": "Накопления", "amount": 400.00}
     ]
   }
   ```

---

## Запуск и тестирование

### Требования

- Python 3.9+
- PostgreSQL

### Установка зависимостей

```bash
# 1. Перейти в папку Python примера
cd lab-02/src_python

# 2. Создать виртуальное окружение
python -m venv venv

# 3. Активировать (Windows)
venv\Scripts\activate

# 3. Активировать (Linux/Mac)
source venv/bin/activate

# 4. Установить зависимости
pip install -r requirements.txt
```

### Вариант 1: CLI (без REST API)

```bash
python example_cli.py
```

**Вывод:**
```
============================================================
Transaction Service - Финучёт «Где мои деньги» 💸
Пример использования гексагональной архитектуры
============================================================

📋 Регистрация дохода...
   Пользователь: user-001
   Сумма: 1000.00
   Комментарий: Зарплата за октябрь

✅ [BudgetRepo] Найдены настройки бюджета:
   - Покушать: 60.0%
   - Накопления: 40.0%

📊 Расчет распределения:
   - Покушать: 600.00 руб.
   - Накопления: 400.00 руб.

💾 [TransactionRepo] Сохранена транзакция: TXN-2024-0042
💰 [CategoryRepo] Обновлены балансы:
   - Покушать: 0.00 → 600.00
   - Накопления: 0.00 → 400.00

============================================================
✅ Транзакция успешно создана!
   ID: TXN-2024-0042
   Статус: COMPLETED
============================================================

📋 Регистрация расхода...
   Пользователь: user-001
   Категория: Покушать
   Сумма: 200.00

💰 Текущий баланс категории: 600.00
✅ После списания: 400.00

============================================================
✅ Расход успешно зарегистрирован!
   ID: TXN-2024-0043
============================================================
```

### Вариант 2: REST API (FastAPI)

```bash
# 1. Запустить FastAPI сервер
python main.py
```

Откроется на: http://localhost:8000

**Интерактивная документация API:** http://localhost:8000/docs

**Создать доход:**
```bash
curl -X POST http://localhost:8000/api/transactions/income \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "amount": 1000.00,
    "description": "Зарплата",
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Создать расход:**
```bash
curl -X POST http://localhost:8000/api/transactions/expense \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "category_id": "CAT-01",
    "amount": 200.00,
    "description": "Обед",
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

**Получить баланс пользователя:**
```bash
curl -X GET http://localhost:8000/api/users/user-001/balance
```

---

## 🔍 Ключевые особенности гексагональной архитектуры

### 1. Dependency Inversion Principle (DIP)

**TransactionService** зависит от **интерфейсов** (портов), а не от конкретных реализаций:

```python
class TransactionService(CreateIncomeUseCase, CreateExpenseUseCase):
    """Application Service реализует use-case"""
    
    def __init__(
        self,
        transaction_repo: TransactionRepository,      # Интерфейс!
        category_repo: CategoryRepository,           # Интерфейс!
        budget_repo: BudgetSettingsRepository        # Интерфейс!
    ):
        self._transaction_repo = transaction_repo
        self._category_repo = category_repo
        self._budget_repo = budget_repo
```

### 2. Атомарность операций

Использование контекстного менеджера для управления БД-транзакциями:

```python
def create_income(self, command: CreateIncomeCommand) -> str:
    # Проверка идемпотентности
    existing = self._transaction_repo.find_by_idempotency_key(
        command.idempotency_key
    )
    if existing:
        return existing.id
    
    # Получение данных
    budget_settings = self._budget_repo.find_by_user_id(command.user_id)
    
    # Бизнес-логика
    transaction = Transaction.create_income(
        user_id=command.user_id,
        amount=command.amount,
        description=command.description,
        budget_settings=budget_settings
    )
    
    # Атомарное сохранение (в одной БД-транзакции)
    with self._transaction_repo.begin_transaction():
        self._transaction_repo.save(transaction)
        for dist in transaction.category_distributions:
            self._category_repo.update_balance(
                dist.category_id,
                dist.amount
            )
    
    return transaction.id
```

### 3. Тестируемость

Легко заменить реальные адаптеры на моки:

```python
def test_create_income_happy_path():
    # Mock адаптеры
    mock_transaction_repo = Mock(spec=TransactionRepository)
    mock_category_repo = Mock(spec=CategoryRepository)
    mock_budget_repo = Mock(spec=BudgetSettingsRepository)
    
    # Настройка моков
    mock_budget_repo.find_by_user_id.return_value = [
        BudgetSetting("CAT-01", Decimal("60"), "user-001"),
        BudgetSetting("CAT-02", Decimal("40"), "user-001")
    ]
    mock_transaction_repo.find_by_idempotency_key.return_value = None
    
    # Сервис с моками
    service = TransactionService(
        mock_transaction_repo,
        mock_category_repo,
        mock_budget_repo
    )
    
    # Выполнение use-case
    command = CreateIncomeCommand(
        user_id="user-001",
        amount=Decimal("1000"),
        description="Зарплата",
        idempotency_key="test-key"
    )
    transaction_id = service.create_income(command)
    
    # Проверки
    mock_transaction_repo.save.assert_called_once()
    assert mock_category_repo.update_balance.call_count == 2
    
    # Проверка сумм распределения
    saved_transaction = mock_transaction_repo.save.call_args[0][0]
    assert saved_transaction.amount == Decimal("1000")
    assert saved_transaction.category_distributions[0].amount == Decimal("600")
    assert saved_transaction.category_distributions[1].amount == Decimal("400")
```

### 4. Замена адаптеров без изменения бизнес-логики

**Было:** InMemoryTransactionRepository  
**Стало:** PostgreSQLTransactionRepository

**TransactionService не изменился!** Только конфигурация DI:

```python
# В dependency_injection.py

class DependencyContainer:
    def __init__(self, use_postgres: bool = False):
        if use_postgres:
            self._transaction_repo = PostgreSQLTransactionRepository()
            self._category_repo = PostgreSQLCategoryRepository()
            self._budget_repo = PostgreSQLBudgetRepository()
        else:
            self._transaction_repo = InMemoryTransactionRepository()
            self._category_repo = InMemoryCategoryRepository()
            self._budget_repo = InMemoryBudgetRepository()
    
    def get_transaction_service(self) -> TransactionService:
        return TransactionService(
            self._transaction_repo,
            self._category_repo,
            self._budget_repo
        )
```

---

## 📊 Обработка исключительных ситуаций (из Lab #1)

### 1. Недостаточно средств в категории

```python
def create_expense(self, command: CreateExpenseCommand) -> str:
    # Проверка идемпотентности
    existing = self._transaction_repo.find_by_idempotency_key(
        command.idempotency_key
    )
    if existing:
        return existing.id
    
    # Получение категории с блокировкой
    category = self._category_repo.find_by_id_with_lock(command.category_id)
    
    if category.balance < command.amount and not command.allow_negative:
        raise InsufficientFundsError(
            f"Недостаточно средств в категории {category.name}. "
            f"Доступно: {category.balance}, требуется: {command.amount}"
        )
    
    # Создание и сохранение транзакции
    transaction = Transaction.create_expense(
        user_id=command.user_id,
        category_id=command.category_id,
        amount=command.amount,
        description=command.description
    )
    
    with self._transaction_repo.begin_transaction():
        self._transaction_repo.save(transaction)
        self._category_repo.update_balance(
            command.category_id,
            category.balance - command.amount
        )
    
    return transaction.id
```

---

## 📚 Связь с Lab #1

| Элемент Lab #1 | Элемент Lab #2 | Описание |
|----------------|----------------|----------|
| Use-case "Добавление дохода" | `CreateIncomeUseCase` | Интерфейс для основного сценария |
| Use-case "Добавление расхода" | `CreateExpenseUseCase` | Интерфейс для сценария расхода |
| Сущность Transaction | `domain/transaction.py` | Агрегат с бизнес-правилами |
| Сущность Category | `domain/category.py` | Entity с бизнес-правилами |
| Gherkin сценарий "Успешное добавление" | `TransactionService.create_income()` | Реализация happy path |
| Транзакция "Сохранение + обновление балансов" | `TransactionService` с begin_transaction() | Атомарность операций |
| Sequence diagram | Architecture diagram | Визуализация взаимодействия слоёв |
| Обработка исключений | Custom exceptions + rollback | Стратегии обработки ошибок |
| Идемпотентность | Проверка `idempotency_key` | Предотвращение дублирования |

---

## 💡 Что изучить дальше

- **Lab #3:** Domain Layer - углубленное моделирование агрегатов Transaction и Category
- **Lab #4:** Application Layer - CQRS разделение команд и запросов
- **Lab #5:** Infrastructure Layer - интеграция с PostgreSQL, Redis, Message Queue

---

## 📝 Контрольные вопросы (для защиты)

1. **Как в гексагональной архитектуре реализована атомарность операции распределения дохода?**
   - Используется паттерн Unit of Work: все изменения (сохранение транзакции + обновление балансов категорий) выполняются в одной БД-транзакции.

2. **Где находится бизнес-логика распределения дохода по категориям?**
   - В Domain Layer (метод `Transaction.create_income()`), так как это core business rule.

3. **Как обеспечить идемпотентность при повторных запросах?**
   - Клиент генерирует `idempotency_key`, сервер проверяет его перед созданием транзакции.

4. **Как тестировать TransactionService без реальной базы данных?**
   - Через mock-объекты, реализующие исходящие порты (репозитории).

5. **Что произойдёт при ошибке обновления баланса категории?**
   - БД-транзакция откатится, транзакция не будет сохранена, пользователь получит ошибку.

6. **Как обрабатывается конкурентное обновление баланса?**
   - Используется оптимистичная блокировка с версионированием или `SELECT FOR UPDATE`.

7. **Почему операции с отчетами вынесены в асинхронную очередь?**
   - Чтобы не блокировать основной поток и улучшить отзывчивость системы.

8. **Как изменить хранилище с InMemory на PostgreSQL без изменения бизнес-логики?**
   - Создать новый адаптер, реализующий тот же порт (интерфейс), и заменить в DI-контейнере.

---

## 🔗 Ссылки

- **Репозиторий:** https://github.com/Katapo13/PIS-2026/lab-02
- **Lab #1 (Transaction Scenario):** https://github.com/Katapo13/PIS-2026/lab-01
- **Документация FastAPI:** https://fastapi.tiangolo.com/
- **Гексагональная архитектура:** https://alistair.cockburn.us/hexagonal-architecture/

---

**Дата выполнения:** 28 марта 2026

**Оценка:** _____________

**Подпись преподавателя:** _____________