# Лабораторная работа №5. Infrastructure Layer (Инфраструктурный слой)

**Дисциплина:** Проектирование интернет-систем  
**Тема:** Реализация Repository, REST API, БД

---

> 🚧 **Важно!** Эта лаба **продолжает Lab #2-4**. Вы реализуете **адаптеры** для портов, созданных ранее.

---

## Цель работы

Реализовать **инфраструктурный слой** (Infrastructure Layer):
- **Repository** - сохранение агрегатов в PostgreSQL
- **REST Controller** - HTTP API для команд/запросов
- **Event Publisher** - публикация доменных событий

---

## Результаты обучения

После выполнения работы студент будет:
- **Реализовывать** исходящие адаптеры (Repository)
- **Создавать** входящие адаптеры (REST Controller)
- **Настраивать** ORM (SQLAlchemy), миграции (Alembic)
- **Тестировать** интеграцию с БД (testcontainers)

---

## Задание

### Часть 1. Repository (Исходящий адаптер)

Реализуйте интерфейс `RequestRepository` (из Lab #2) с **PostgreSQL**.

**Требования:**
- Реализация интерфейса из `application.port.out`
- ORM-маппинг (SQLAlchemy)
- Методы: `save()`, `find_by_id()`, `find_active_requests()`

📖 **Пример:** [examples/infrastructure/adapter/out/request_repository_impl.py](examples/infrastructure/adapter/out/request_repository_impl.py)

---

### Часть 2. REST Controller (Входящий адаптер)

Создайте HTTP API для команд и запросов.

**Эндпоинты:**
- `POST /api/requests` - создать заявку
- `POST /api/requests/{id}/assign-group` - назначить группу
- `GET /api/requests/{id}` - получить заявку
- `GET /api/requests` - список активных заявок

📖 **Пример:** [examples/infrastructure/adapter/in/request_controller.py](examples/infrastructure/adapter/in/request_controller.py)

---

### Часть 3. БД и миграции

**Настройка PostgreSQL:**
- Docker Compose для локального запуска
- Миграции Alembic

📖 **Пример:** [examples/docker-compose.yml](examples/docker-compose.yml)

---

<!-- START:artifacts -->
## Структура отчёта

📄 **[Макет отчёта →](Макет_отчета.md)**

```
lab-05/
├── Отчет.md
├── infrastructure/
│   ├── adapter/
│   │   ├── in/
│   │   │   └── request_controller.py     # FastAPI
│   │   └── out/
│   │       └── request_repository.py      # SQLAlchemy
│   ├── config/
│   │   └── database.py                   # DB connection
│   └── migrations/                       # Alembic
│       └── versions/
├── docker-compose.yml
└── tests/
    └── test_integration.py
```
<!-- END:artifacts -->

<!-- START:criteria -->
## Критерии оценки

| Критерий | Баллы | Требования |
|----------|-------|------------|
| Repository: реализация интерфейса, ORM | 25 | SQLAlchemy, методы save/find |
| REST Controller: CRUD операции | 25 | POST/GET endpoints, JSON |
| БД: миграции, Docker Compose | 15 | Alembic, PostgreSQL |
| Event Publisher: публикация событий | 15 | In-memory или Kafka |
| Интеграционные тесты: testcontainers | 15 | Тесты с реальной БД |
| Качество документации | 5 | README, OpenAPI |
| **ИТОГО** | **100** | |
<!-- END:criteria -->

<!-- START:bonuses -->
## Бонусы (+ до 15)

* **Docker Compose для всей системы** (+5) - app + db + migrations
* **OpenAPI Swagger UI** (+4) - автодокументация API
* **Health Check endpoint** (+3) - `/health` с проверкой БД
* **CORS configuration** (+3) - настройка для фронтенда
<!-- END:bonuses -->

## Контрольные вопросы для защиты

1. **Почему Repository находится в Infrastructure, а не в Domain?**
2. **В чём преимущество ORM над обычным SQL?**
3. **Зачем использовать миграции вместо ручного CREATE TABLE?**
4. **Как testcontainers упрощает интеграционное тестирование?**
5. **Почему REST Controller не вызывает напрямую доменные модели?**

---

## Полезные ресурсы

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Testcontainers](https://testcontainers.com/)

---

## Срок сдачи

**Неделя 10-11 семестра**  
Защита: демонстрация работы API через Postman/Swagger
