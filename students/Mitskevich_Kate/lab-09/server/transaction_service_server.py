import grpc
import logging
import time
import threading
from concurrent import futures
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

# Импорт сгенерированных классов
import sys
sys.path.append('./generated')
import transaction_service_pb2
import transaction_service_pb2_grpc

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# DOMAIN MODELS (упрощённые для gRPC)
# ========================================

@dataclass
class TransactionData:
    """Внутреннее представление транзакции"""
    id: str
    type: str
    amount: Decimal
    user_id: str
    status: str
    idempotency_key: str
    description: Optional[str]
    distributions: List[dict]
    created_at: int
    updated_at: int


@dataclass
class CategoryData:
    """Внутреннее представление категории"""
    id: str
    name: str
    user_id: str
    balance: Decimal
    budget_percentage: Optional[Decimal]
    created_at: int
    updated_at: int
    version: int


# ========================================
# GRPC SERVER IMPLEMENTATION
# ========================================

class TransactionServiceServicer(transaction_service_pb2_grpc.TransactionServiceServicer):
    """
    gRPC Server: Transaction Service
    Реализация всех RPC методов
    """
    
    def __init__(self):
        # In-memory storage (в реальности: PostgreSQL)
        self._transactions: Dict[str, TransactionData] = {}
        self._categories: Dict[str, CategoryData] = {}
        self._budget_settings: Dict[str, List[dict]] = defaultdict(list)
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> transaction_id
        
        # Счётчики для генерации ID
        self._transaction_counter = 0
        self._category_counter = 0
        
        # Для streaming: список подписчиков
        self._stream_subscribers: Dict[str, List] = defaultdict(list)
        self._stream_lock = threading.Lock()
        
        # Инициализация тестовыми данными
        self._init_test_data()
    
    def _init_test_data(self):
        """Инициализация тестовыми данными"""
        # Категории для пользователя user-001
        categories = [
            CategoryData(
                id="CAT-01",
                name="Покушать",
                user_id="user-001",
                balance=Decimal("600"),
                budget_percentage=Decimal("60"),
                created_at=int(time.time()),
                updated_at=int(time.time()),
                version=1
            ),
            CategoryData(
                id="CAT-02",
                name="Накопления",
                user_id="user-001",
                balance=Decimal("400"),
                budget_percentage=Decimal("40"),
                created_at=int(time.time()),
                updated_at=int(time.time()),
                version=1
            ),
            CategoryData(
                id="CAT-03",
                name="Развлечения",
                user_id="user-001",
                balance=Decimal("200"),
                budget_percentage=None,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                version=1
            ),
        ]
        
        for cat in categories:
            self._categories[cat.id] = cat
        
        # Настройки бюджета
        self._budget_settings["user-001"] = [
            {"category_id": "CAT-01", "category_name": "Покушать", "percentage": Decimal("60")},
            {"category_id": "CAT-02", "category_name": "Накопления", "percentage": Decimal("40")},
        ]
        
        logger.info("Test data initialized: 3 categories for user-001")
    
    def _generate_transaction_id(self) -> str:
        """Генерация ID транзакции: TXN-2026-XXXXX"""
        self._transaction_counter += 1
        year = time.localtime().tm_year
        return f"TXN-{year}-{self._transaction_counter:05d}"
    
    def _calculate_distribution(self, amount: Decimal, user_id: str) -> List[dict]:
        """Расчёт распределения дохода по категориям"""
        settings = self._budget_settings.get(user_id, [])
        
        if not settings:
            # Нет настроек - вся сумма в нераспределённое
            return [{
                "category_id": "uncategorized",
                "category_name": "Нераспределенное",
                "amount": amount
            }]
        
        distributions = []
        remaining = amount
        
        for i, setting in enumerate(settings):
            if i == len(settings) - 1:
                # Последняя категория получает остаток
                dist_amount = remaining
            else:
                dist_amount = (amount * setting["percentage"] / Decimal("100")).quantize(Decimal("0.01"))
                remaining -= dist_amount
            
            distributions.append({
                "category_id": setting["category_id"],
                "category_name": setting["category_name"],
                "amount": dist_amount
            })
        
        return distributions
    
    def _update_category_balance(self, category_id: str, delta: Decimal) -> bool:
        """Обновление баланса категории"""
        category = self._categories.get(category_id)
        if not category:
            return False
        
        category.balance += delta
        category.updated_at = int(time.time())
        category.version += 1
        return True
    
    def _notify_subscribers(self, user_id: str, transaction: TransactionData):
        """Уведомление подписчиков стрима о новой транзакции"""
        with self._stream_lock:
            if user_id in self._stream_subscribers:
                for subscriber in self._stream_subscribers[user_id]:
                    try:
                        # Конвертируем в protobuf и отправляем
                        pb_transaction = self._to_proto_transaction(transaction)
                        subscriber.put(pb_transaction)
                    except Exception as e:
                        logger.error(f"Failed to notify subscriber: {e}")
    
    def _to_proto_transaction(self, tx: TransactionData) -> transaction_service_pb2.Transaction:
        """Конвертация внутреннего представления в protobuf"""
        # Определение типа
        if tx.type == "INCOME":
            tx_type = transaction_service_pb2.TRANSACTION_TYPE_INCOME
        else:
            tx_type = transaction_service_pb2.TRANSACTION_TYPE_EXPENSE
        
        # Определение статуса
        if tx.status == "PENDING":
            status = transaction_service_pb2.TRANSACTION_STATUS_PENDING
        elif tx.status == "COMPLETED":
            status = transaction_service_pb2.TRANSACTION_STATUS_COMPLETED
        else:
            status = transaction_service_pb2.TRANSACTION_STATUS_FAILED
        
        # Распределения
        distributions = []
        for dist in tx.distributions:
            distributions.append(transaction_service_pb2.CategoryDistribution(
                category_id=dist["category_id"],
                category_name=dist["category_name"],
                amount=float(dist["amount"])
            ))
        
        return transaction_service_pb2.Transaction(
            id=tx.id,
            type=tx_type,
            amount=float(tx.amount),
            user_id=tx.user_id,
            status=status,
            idempotency_key=tx.idempotency_key,
            description=tx.description,
            distributions=distributions,
            created_at=tx.created_at,
            updated_at=tx.updated_at
        )
    
    # ========================================
    # UNARY RPC IMPLEMENTATIONS
    # ========================================
    
    def CreateIncome(self, request, context):
        """Регистрация дохода"""
        logger.info(f"CreateIncome: user={request.user_id}, amount={request.amount}")
        
        # 1. Проверка идемпотентности
        if request.idempotency_key in self._idempotency_map:
            tx_id = self._idempotency_map[request.idempotency_key]
            tx = self._transactions.get(tx_id)
            if tx:
                logger.info(f"Idempotent request: returning existing transaction {tx_id}")
                return transaction_service_pb2.CreateIncomeResponse(
                    transaction_id=tx.id,
                    status=self._to_proto_transaction(tx).status,
                    distributions=self._to_proto_transaction(tx).distributions
                )
        
        # 2. Валидация суммы
        amount = Decimal(str(request.amount))
        if amount <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Сумма дохода должна быть больше 0")
            return transaction_service_pb2.CreateIncomeResponse(
                status=transaction_service_pb2.TRANSACTION_STATUS_FAILED,
                error_message="Сумма дохода должна быть больше 0"
            )
        
        # 3. Расчёт распределения
        distributions = self._calculate_distribution(amount, request.user_id)
        
        # 4. Создание транзакции
        tx_id = self._generate_transaction_id()
        transaction = TransactionData(
            id=tx_id,
            type="INCOME",
            amount=amount,
            user_id=request.user_id,
            status="PENDING",
            idempotency_key=request.idempotency_key,
            description=request.description,
            distributions=distributions,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        # 5. Обновление балансов категорий
        try:
            for dist in distributions:
                if dist["category_id"] != "uncategorized":
                    self._update_category_balance(dist["category_id"], dist["amount"])
            
            transaction.status = "COMPLETED"
            transaction.updated_at = int(time.time())
            self._transactions[tx_id] = transaction
            self._idempotency_map[request.idempotency_key] = tx_id
            
            logger.info(f"Income transaction {tx_id} completed successfully")
            
            # Уведомление подписчиков
            self._notify_subscribers(request.user_id, transaction)
            
            # Конвертируем распределения в protobuf
            pb_distributions = []
            for dist in distributions:
                pb_distributions.append(transaction_service_pb2.CategoryDistribution(
                    category_id=dist["category_id"],
                    category_name=dist["category_name"],
                    amount=float(dist["amount"])
                ))
            
            return transaction_service_pb2.CreateIncomeResponse(
                transaction_id=tx_id,
                status=transaction_service_pb2.TRANSACTION_STATUS_COMPLETED,
                distributions=pb_distributions
            )
            
        except Exception as e:
            logger.error(f"Failed to create income: {e}")
            transaction.status = "FAILED"
            self._transactions[tx_id] = transaction
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return transaction_service_pb2.CreateIncomeResponse(
                status=transaction_service_pb2.TRANSACTION_STATUS_FAILED,
                error_message=str(e)
            )
    
    def CreateExpense(self, request, context):
        """Регистрация расхода"""
        logger.info(f"CreateExpense: user={request.user_id}, category={request.category_id}, amount={request.amount}")
        
        # 1. Проверка идемпотентности
        if request.idempotency_key in self._idempotency_map:
            tx_id = self._idempotency_map[request.idempotency_key]
            tx = self._transactions.get(tx_id)
            if tx:
                return transaction_service_pb2.CreateExpenseResponse(
                    transaction_id=tx.id,
                    status=self._to_proto_transaction(tx).status,
                    new_balance=0.0
                )
        
        # 2. Валидация
        amount = Decimal(str(request.amount))
        if amount <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Сумма расхода должна быть больше 0")
            return transaction_service_pb2.CreateExpenseResponse(
                status=transaction_service_pb2.TRANSACTION_STATUS_FAILED,
                error_message="Сумма расхода должна быть больше 0"
            )
        
        # 3. Получение категории
        category = self._categories.get(request.category_id)
        if not category:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Категория {request.category_id} не найдена")
            return transaction_service_pb2.CreateExpenseResponse(
                status=transaction_service_pb2.TRANSACTION_STATUS_FAILED,
                error_message="Категория не найдена"
            )
        
        # 4. Проверка баланса
        if not request.allow_negative and category.balance < amount:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(f"Недостаточно средств. Доступно: {category.balance}")
            return transaction_service_pb2.CreateExpenseResponse(
                status=transaction_service_pb2.TRANSACTION_STATUS_FAILED,
                error_message=f"Недостаточно средств. Доступно: {category.balance}"
            )
        
        # 5. Создание транзакции
        tx_id = self._generate_transaction_id()
        new_balance = category.balance - amount
        
        transaction = TransactionData(
            id=tx_id,
            type="EXPENSE",
            amount=amount,
            user_id=request.user_id,
            status="COMPLETED",
            idempotency_key=request.idempotency_key,
            description=request.description,
            distributions=[{
                "category_id": category.id,
                "category_name": category.name,
                "amount": amount
            }],
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        # 6. Обновление баланса
        self._update_category_balance(request.category_id, -amount)
        self._transactions[tx_id] = transaction
        self._idempotency_map[request.idempotency_key] = tx_id
        
        logger.info(f"Expense transaction {tx_id} completed successfully")
        
        # Уведомление подписчиков
        self._notify_subscribers(request.user_id, transaction)
        
        return transaction_service_pb2.CreateExpenseResponse(
            transaction_id=tx_id,
            status=transaction_service_pb2.TRANSACTION_STATUS_COMPLETED,
            new_balance=float(new_balance)
        )
    
    def GetTransaction(self, request, context):
        """Получение транзакции по ID"""
        logger.info(f"GetTransaction: {request.transaction_id}")
        
        tx = self._transactions.get(request.transaction_id)
        if tx:
            return transaction_service_pb2.GetTransactionResponse(
                transaction=self._to_proto_transaction(tx),
                found=True
            )
        else:
            return transaction_service_pb2.GetTransactionResponse(found=False)
    
    def GetUserBalance(self, request, context):
        """Получение баланса пользователя"""
        logger.info(f"GetUserBalance: {request.user_id}")
        
        total_balance = Decimal("0")
        category_balances = []
        
        for cat in self._categories.values():
            if cat.user_id == request.user_id:
                total_balance += cat.balance
                category_balances.append(transaction_service_pb2.CategoryBalance(
                    category_id=cat.id,
                    category_name=cat.name,
                    balance=float(cat.balance)
                ))
        
        return transaction_service_pb2.GetUserBalanceResponse(
            user_id=request.user_id,
            total_balance=float(total_balance),
            category_balances=category_balances
        )
    
    def GetBudgetSettings(self, request, context):
        """Получение настроек бюджета"""
        logger.info(f"GetBudgetSettings: {request.user_id}")
        
        settings = self._budget_settings.get(request.user_id, [])
        pb_settings = []
        
        for s in settings:
            pb_settings.append(transaction_service_pb2.BudgetSetting(
                category_id=s["category_id"],
                category_name=s["category_name"],
                percentage=float(s["percentage"]),
                user_id=request.user_id
            ))
        
        return transaction_service_pb2.GetBudgetSettingsResponse(settings=pb_settings)
    
    def UpdateBudgetSettings(self, request, context):
        """Обновление настроек бюджета"""
        logger.info(f"UpdateBudgetSettings: {request.user_id}")
        
        # Валидация
        total = sum(s.percentage for s in request.settings)
        if abs(total - 100.0) > 0.01:  # Допуск на округление
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Сумма процентов должна быть 100%, текущая: {total}%")
            return transaction_service_pb2.UpdateBudgetSettingsResponse(
                success=False,
                error_message=f"Сумма процентов должна быть 100%, текущая: {total}%"
            )
        
        # Сохранение
        new_settings = []
        for s in request.settings:
            new_settings.append({
                "category_id": s.category_id,
                "category_name": s.category_name,
                "percentage": Decimal(str(s.percentage))
            })
        
        self._budget_settings[request.user_id] = new_settings
        
        # Обновление процентов в категориях
        for s in request.settings:
            cat = self._categories.get(s.category_id)
            if cat:
                cat.budget_percentage = Decimal(str(s.percentage))
        
        return transaction_service_pb2.UpdateBudgetSettingsResponse(success=True)
    
    def ValidateBudgetSettings(self, request, context):
        """Валидация настроек бюджета"""
        total = sum(s.percentage for s in request.settings)
        valid = abs(total - 100.0) <= 0.01
        
        if valid:
            return transaction_service_pb2.ValidateBudgetSettingsResponse(
                valid=True,
                total_percentage=total
            )
        else:
            return transaction_service_pb2.ValidateBudgetSettingsResponse(
                valid=False,
                total_percentage=total,
                error_message=f"Сумма процентов должна быть 100%, текущая: {total}%"
            )
    
    def GetCategories(self, request, context):
        """Получение всех категорий пользователя"""
        logger.info(f"GetCategories: {request.user_id}")
        
        categories = []
        for cat in self._categories.values():
            if cat.user_id == request.user_id:
                categories.append(transaction_service_pb2.Category(
                    id=cat.id,
                    name=cat.name,
                    user_id=cat.user_id,
                    balance=float(cat.balance),
                    budget_percentage=float(cat.budget_percentage) if cat.budget_percentage else None,
                    created_at=cat.created_at,
                    updated_at=cat.updated_at,
                    version=cat.version
                ))
        
        return transaction_service_pb2.GetCategoriesResponse(categories=categories)
    
    def HealthCheck(self, request, context):
        """Проверка здоровья сервиса"""
        return transaction_service_pb2.HealthCheckResponse(
            status=transaction_service_pb2.HealthCheckResponse.SERVING
        )
    
    # ========================================
    # SERVER-SIDE STREAMING
    # ========================================
    
    def StreamTransactions(self, request, context):
        """
        Server-side Streaming: Стрим транзакций пользователя
        Отправляет все существующие и новые транзакции
        """
        logger.info(f"StreamTransactions started for user {request.user_id}")
        
        # Создаём очередь для этого клиента
        queue = []
        
        with self._stream_lock:
            if request.user_id not in self._stream_subscribers:
                self._stream_subscribers[request.user_id] = []
            self._stream_subscribers[request.user_id].append(queue)
        
        try:
            # Отправляем существующие транзакции
            for tx in self._transactions.values():
                if tx.user_id == request.user_id:
                    # Фильтрация по типу
                    if request.HasField('type_filter'):
                        if request.type_filter == transaction_service_pb2.TRANSACTION_TYPE_INCOME and tx.type != "INCOME":
                            continue
                        if request.type_filter == transaction_service_pb2.TRANSACTION_TYPE_EXPENSE and tx.type != "EXPENSE":
                            continue
                    
                    # Фильтрация по статусу
                    if request.HasField('status_filter'):
                        pb_status = self._to_proto_transaction(tx).status
                        if pb_status != request.status_filter:
                            continue
                    
                    yield self._to_proto_transaction(tx)
                    time.sleep(0.1)  # Небольшая задержка для имитации потока
            
            # Затем ждём новые транзакции
            while context.is_active():
                # Проверяем очередь на наличие новых сообщений
                if queue:
                    tx = queue.pop(0)
                    yield tx
                else:
                    time.sleep(0.5)  # Ожидание новых транзакций
                    
        except Exception as e:
            logger.error(f"StreamTransactions error: {e}")
        finally:
            # Очистка подписки
            with self._stream_lock:
                if request.user_id in self._stream_subscribers:
                    self._stream_subscribers[request.user_id] = [
                        q for q in self._stream_subscribers[request.user_id] 
                        if q != queue
                    ]
            
            logger.info(f"StreamTransactions ended for user {request.user_id}")


# ========================================
# SERVER LAUNCH
# ========================================

def serve():
    """Запуск gRPC сервера"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transaction_service_pb2_grpc.add_TransactionServiceServicer_to_server(
        TransactionServiceServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    
    logger.info("=" * 60)
    logger.info("🚀 Transaction Service gRPC Server started")
    logger.info("📡 Listening on port 50051")
    logger.info("=" * 60)
    logger.info("Available RPC methods:")
    logger.info("  • CreateIncome")
    logger.info("  • CreateExpense")
    logger.info("  • GetTransaction")
    logger.info("  • GetUserBalance")
    logger.info("  • GetBudgetSettings")
    logger.info("  • UpdateBudgetSettings")
    logger.info("  • ValidateBudgetSettings")
    logger.info("  • GetCategories")
    logger.info("  • StreamTransactions (server streaming)")
    logger.info("  • HealthCheck")
    logger.info("=" * 60)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down server...")
        server.stop(0)


if __name__ == '__main__':
    serve()