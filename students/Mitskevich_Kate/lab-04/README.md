# Лабораторная работа №4. Application Layer (Прикладной слой)

**Дисциплина:** Проектирование интернет-систем  
**Тема:** Команды, Запросы, Обработчики (CQRS на уровне интерфейса)

---

> 🚧 **Важно!** Эта лаба **продолжает Lab #3**. Вы используете доменный слой (Request, Group, Zone) и добавляете **прикладной слой** (Commands, Queries, Handlers).

---

## Цель работы

Реализовать **прикладной слой** (Application Layer) с разделением операций на:
- **Команды** (Commands) - изменяют состояние домена
- **Запросы** (Queries) - читают данные без изменений

Это паттерн **CQRS (Command Query Responsibility Segregation)** на уровне интерфейса.

---

## Результаты обучения

После выполнения работы студент будет:
- **Различать** команды и запросы (Command/Query Separation)
- **Проектировать** Command Handlers и Query Handlers
- **Реализовывать** валидацию на уровне приложения (не домена!)
- **Применять** паттерн Use Case / Interactor / Service

---

## Теоретическая справка

### Зачем нужен Application Layer?

**Domain Layer** (Lab #3):
- Бизнес-логика, инварианты
- Не знает о HTTP, БД, JSON

**Application Layer** (эта лаба):
- **Оркестрирует** вызовы домена
- **Валидирует** входные данные (перед доменом)
- **Координирует** транзакции, события, репозитории

**Infrastructure Layer** (Lab #5):
- HTTP контроллеры, БД, файлы

### Command vs Query

| Аспект | Command | Query |
|--------|---------|-------|
| **Назначение** | Изменяет состояние | Читает данные |
| **Возвращает** | `void` или ID | DTO/модель |
| **Примеры** | CreateRequest, AssignGroup | GetRequestById, ListActiveRequests |

### Архитектура этого слоя

```
application/
├── command/
│   ├── CreateRequestCommand
│   └── CreateRequestHandler
├── query/
│   ├── GetRequestByIdQuery
│   └── GetRequestByIdHandler
└── port/
    ├── in/
    │   └── RequestService (интерфейс из Lab #2)
    └── out/
        └── RequestRepository (интерфейс из Lab #2)
```

---

## Задание

⚠️ **Используйте доменный слой из Lab #3** (Request, Group, Zone, события)

### Часть 1. Команды (Commands)

Создайте **DTO-классы** для команд, которые **изменяют** состояние системы.

📖 **Примеры готовых команд:** см. [examples/application/command/](examples/application/command/)

**Команды для Request Service** (ПСО):
- `CreateRequestCommand` - создать новую заявку
- `AssignGroupToRequestCommand` - назначить группу на заявку
- `ActivateRequestCommand` - активировать операцию
- `ChangeRequestZoneCommand` - изменить зону поиска
- `CompleteRequestCommand` - завершить операцию

**Требования к командам:**
- Иммутабельные DTO (dataclass frozen=True)
- Без бизнес-логики (только данные)
- Валидация примитивов (NotBlank, Positive и т.д.)

📖 **Готовые примеры команд:** [examples/application/command/](examples/application/command/)

---

### Часть 2. Обработчики команд (Command Handlers)

Каждая команда обрабатывается **отдельным классом**.

**Шаги обработки:**
1. Валидация входных данных
2. Создание/загрузка агрегата из домена
3. Вызов методов агрегата
4. Сохранение через Repository
5. Публикация доменных событий

**Требования:**
- Один Handler на одну Command
- Транзакционность (`@Transactional` или ручное управление)
- Публикация Domain Events после сохранения

📖 **Готовые примеры handlers:** [examples/application/command/handlers/](examples/application/command/handlers/)

---

### Часть 3. Запросы (Queries)

Создайте DTO для запросов, которые **только читают** данные (без изменений).

**Запросы для Request Service:**
- `GetRequestByIdQuery` - получить заявку по ID
- `ListActiveRequestsQuery` - список активных заявок
- `GetRequestsByCoordinatorQuery` - заявки координатора

**Read DTOs (результаты):**
- `RequestDto` - упрощённая модель для чтения
- `GroupDto`, `ZoneDto` - вложенные объекты

📖 **Готовые примеры queries:** [examples/application/query/](examples/application/query/)

---

### Часть 4. Обработчики запросов (Query Handlers)

**Задача Query Handler:**
- Извлечь данные через Repository
- Преобразовать доменные модели в Read DTOs
- **НЕ изменять** состояние системы

📖 **Готовые примеры:** [examples/application/query/handlers/](examples/application/query/handlers/)

---

### Часть 5. Application Service (фасад)

Создайте **сервис-фасад**, который делегирует вызовы Command/Query Handlers.

**Пример интерфейса** (из Lab #2):
```python
class RequestService(ABC):
    @abstractmethod
    def create_request(self, command: CreateRequestCommand) -> str:
        """Создать заявку. Возвращает ID."""
        pass
    
    @abstractmethod
    def get_request_by_id(self, query: GetRequestByIdQuery) -> RequestDto:
        """Получить заявку по ID."""
        pass
```

📖 **Готовая реализация:** [examples/application/service/request_service_impl.py](examples/application/service/request_service_impl.py)

---

<!-- START:artifacts -->
## Структура отчёта

📄 **[Макет отчёта →](Макет_отчета.md)**

Создайте в **своём репозитории** папку `lab-04/`:

```
lab-04/
├── Отчет.md
├── application/
│   ├── command/
│   │   ├── create_request_command.py
│   │   ├── assign_group_command.py
│   │   └── handlers/
│   │       ├── create_request_handler.py
│   │       └── assign_group_handler.py
│   ├── query/
│   │   ├── get_request_by_id_query.py
│   │   └── handlers/
│   │       └── get_request_by_id_handler.py
│   └── service/
│       └── request_service.py  # Фасад
└── tests/
    ├── test_create_request_handler.py
    └── test_queries.py
```
<!-- END:artifacts -->

<!-- START:criteria -->
## Критерии оценки

| Критерий | Баллы | Требования |
|----------|-------|------------|
| Команды (DTOs) | 15 | Иммутабельные, без логики, валидация примитивов |
| Command Handlers | 25 | Один handler на команду, транзакции, события |
| Запросы (DTOs) | 10 | Read-модели, без побочных эффектов |
| Query Handlers | 15 | Преобразование домена в DTO, без изменений |
| Application Service (фасад) | 20 | Делегирование вызовов handlers |
| Юнит-тесты handlers | 10 | Mocker для репозиториев, проверка событий |
| Качество документации | 5 | Оформление, README |
| **ИТОГО** | **100** | |
<!-- END:criteria -->

<!-- START:bonuses -->
## Бонусы (+ до 15)

* **REST API контроллер** (+5) - HTTP endpoints для команд/запросов
* **Bean Validation** (+4) - аннотации валидации (@NotBlank, @Valid)
* **Exception Handling** (+3) - глобальный обработчик ошибок
* **OpenAPI документация** (+3) - Swagger/OpenAPI спецификация
<!-- END:bonuses -->

## Контрольные вопросы для защиты

1. **В чём разница между Command и Query?**
   - Command изменяет состояние, Query только читает
   - Command возвращает void/ID, Query возвращает DTO

2. **Почему Command Handler возвращает только ID, а не весь объект?**
   - Избежать утечки доменной модели наружу
   - Клиент должен делать отдельный GET-запрос (CQRS)

3. **Где должна выполняться валидация: в команде, обработчике или доменной модели?**
   - **Примитивы** - в команде/обработчике (NotBlank, Positive)
   - **Инварианты** - в доменной модели (количество участников группы)

4. **Можно ли вызывать Query из Command Handler?**
   - Технически можно, но **не рекомендуется** (нарушает CQRS)
   - Лучше загружать данные через Repository

5. **Зачем разделять Request DTO (от клиента) и Command (внутренний)?**
   - Request DTO - HTTP/JSON формат
   - Command - внутренняя структура приложения
   - Разделение позволяет независимо менять API и бизнес-логику

---

## Полезные ресурсы

### 🚀 Примеры кода
- **[examples/](examples/)** - полная реализация для Request Service

### 📖 Документация
- **[Макет отчёта](Макет_отчета.md)**

### 🔗 Внешние ресурсы
- [CQRS](https://martinfowler.com/bliki/CQRS.html) - Martin Fowler
- [Command Query Separation](https://en.wikipedia.org/wiki/Command%E2%80%93query_separation)

---

## Срок сдачи

**Неделя 8-9 семестра**  
Защита: демонстрация работы handlers + ответы на вопросы

