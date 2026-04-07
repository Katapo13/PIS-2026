# CQRS Read Models - Request Service

Примеры реализации **CQRS** с разделением моделей для **Request Service** (ПСО «Юго-Запад»).

---

## Структура

```
cqrs/
├── write_model/
│   └── request.py                  # Агрегат (как в Lab #3)
├── read_model/
│   ├── request_view.py             # Денормализованная модель
│   └── request_view_repository.py  # Чтение из view
├── projection/
│   ├── request_projection.py       # Event → View sync
│   └── event_handlers.py
└── sql/
    └── materialized_view.sql       # PostgreSQL MATERIALIZED VIEW
```

---

## CQRS: Write Model vs Read Model

### Write Model (Запись)

**Цель:** Изменение состояния системы

**Характеристики:**
- Нормализованная структура
- Инварианты, бизнес-правила
- Доменные события
- Оптимизация для **записи**

**Пример:** Request (aggregate root)

```python
# Агрегат Request из domain/
request = Request("REQ-2024-0001", "COORD-1", zone)
request.assign_group(group)  # Инварианты проверяются
request.activate()           # События генерируются
repository.save(request)     # Сохранение в requests, zones, groups таблицы
```

---

### Read Model (Чтение)

**Цель:** Быстрое чтение данных для UI

**Характеристики:**
- Денормализованная структура (JOIN предзагружен)
- Без бизнес-логики
- Без событий
- Оптимизация для **чтения**

**Пример:** RequestView (projection)

```python
# Проекция RequestView
view = RequestView(
    request_id="REQ-2024-0001",
    coordinator_name="Иван Иванов",      # JOIN с coordinators
    zone_name="North",
    group_leader_name="Пётр Петров",     # JOIN с groups, volunteers
    group_members_count=5,
    status="ACTIVE"
)
```

**Запрос:**
```sql
SELECT * FROM request_view WHERE request_id = 'REQ-2024-0001';
-- Один SELECT вместо 5 JOINов
```

---

## Синхронизация моделей

### Event-Driven Approach

```
Write Model                   Event Bus                Read Model
┌─────────────┐              ┌────────┐              ┌──────────────┐
│ Request     │ ─── emit ──> │ Events │ ─── sync ─>  │ RequestView  │
│ (aggregate) │              └────────┘              │ (projection) │
└─────────────┘                                      └──────────────┘
     │                                                       │
     │ save()                                                │ update()
     ▼                                                       ▼
┌─────────────┐                                      ┌──────────────┐
│ PostgreSQL  │                                      │ PostgreSQL   │
│ (requests)  │                                      │ (views)      │
└─────────────┘                                      └──────────────┘
```

**События:**
- `RequestCreated` → создать RequestView
- `GroupAssigned` → обновить group_leader_name, members_count
- `RequestActivated` → обновить status, activated_at
- `RequestCompleted` → обновить status, completed_at

---

## Примеры использования

### 1. Создание заявки (Write Model)

```python
from application.command.create_request_command import CreateRequestCommand
from application.command.handlers.create_request_handler import CreateRequestHandler

# Command → Write Model
command = CreateRequestCommand(...)
handler = CreateRequestHandler(request_repository, event_publisher)
request_id = handler.handle(command)

# Доменное событие публикуется
event = RequestCreated(request_id, coordinator_id, zone_name)
event_bus.publish(event)
```

### 2. Обновление проекции (Projection Handler)

```python
from cqrs.projection.request_projection import RequestProjection

# Event Handler
@event_handler("RequestCreated")
def on_request_created(event: RequestCreated):
    projection = RequestProjection(view_repository)
    projection.on_request_created(event)
    # → INSERT INTO request_view (...)
```

### 3. Чтение данных (Read Model)

```python
from cqrs.read_model.request_view_repository import RequestViewRepository

# Query → Read Model (без JOINов)
repo = RequestViewRepository(session)
view = repo.find_by_id("REQ-2024-0001")

# Моментальный доступ к денормализованным данным
print(view.coordinator_name)  # Уже загружено
print(view.group_leader_name) # Без дополнительных запросов
```

---

## Materialized Views (PostgreSQL)

### SQL для создания

```sql
CREATE MATERIALIZED VIEW request_view AS
SELECT 
    r.request_id,
    r.status,
    c.name AS coordinator_name,
    z.name AS zone_name,
    g.group_id,
    v.name AS group_leader_name,
    COUNT(gm.volunteer_id) AS group_members_count,
    r.created_at,
    r.activated_at,
    r.completed_at
FROM requests r
LEFT JOIN coordinators c ON r.coordinator_id = c.coordinator_id
LEFT JOIN zones z ON r.zone_id = z.zone_id
LEFT JOIN groups g ON r.assigned_group_id = g.group_id
LEFT JOIN volunteers v ON g.leader_id = v.volunteer_id
LEFT JOIN group_members gm ON g.group_id = gm.group_id
GROUP BY r.request_id, c.name, z.name, g.group_id, v.name;

-- Индекс для быстрого поиска
CREATE UNIQUE INDEX idx_request_view_id ON request_view (request_id);

-- Обновление view (ручное или автоматическое)
REFRESH MATERIALIZED VIEW request_view;
```

### Автоматическое обновление (PostgreSQL 13+)

```sql
-- Создание триггера для автообновления
CREATE OR REPLACE FUNCTION refresh_request_view()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY request_view;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_refresh_request_view
AFTER INSERT OR UPDATE OR DELETE ON requests
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_request_view();
```

---

## Eventual Consistency

**Проблема:** Read Model обновляется асинхронно (через события).

**Сценарий:**
1. Пользователь создаёт заявку → `POST /requests`
2. Request сохраняется в Write Model → 201 Created
3. Событие `RequestCreated` публикуется
4. **Задержка 100ms** (обработка события)
5. RequestView обновляется
6. Пользователь делает `GET /requests/{id}` → **404 Not Found** (если сразу)

**Решения:**
- **Accept 202 Accepted** вместо 201 Created
- **Polling** - клиент переспрашивает
- **WebSocket** - сервер уведомляет клиента
- **Версионирование** - ETag, If-Match

---

## Преимущества CQRS

✅ **Производительность чтения** - нет JOINов  
✅ **Независимое масштабирование** - Read/Write отдельные БД  
✅ **Гибкость** - разные модели для разных UI  
✅ **Оптимизация** - индексы только для Read Model

---

## Недостатки CQRS

❌ **Сложность** - две модели вместо одной  
❌ **Eventual Consistency** - данные не сразу согласованы  
❌ **Дублирование** - одни и те же данные в двух местах  
❌ **Синхронизация** - нужен Event Bus

---

## Когда использовать CQRS?

### ✅ Используйте CQRS когда:

- Сложные запросы с множеством JOINов
- Высокая нагрузка на чтение (чтений в 10+ раз больше записей)
- Разные модели для разных UI (админка, мобильное приложение)
- Event Sourcing уже используется

### ❌ Не используйте CQRS когда:

- Простая CRUD-система
- Нагрузка на чтение/запись примерно равна
- Команда маленькая (overhead не окупается)
- Eventual Consistency неприемлема
