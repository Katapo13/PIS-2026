import grpc
import logging
import time
import sys
from typing import Optional

# Импорт сгенерированных классов
sys.path.append('./generated')
import transaction_service_pb2
import transaction_service_pb2_grpc

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionServiceClient:
    """Клиент для Transaction Service gRPC"""
    
    def __init__(self, host: str = 'localhost', port: int = 50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = transaction_service_pb2_grpc.TransactionServiceStub(self.channel)
    
    def close(self):
        """Закрытие канала"""
        self.channel.close()
    
    # ========================================
    # UNARY RPC CALLS
    # ========================================
    
    def create_income(self, user_id: str, amount: float, idempotency_key: str,
                      description: Optional[str] = None, source: Optional[str] = None):
        """Создание дохода"""
        request = transaction_service_pb2.CreateIncomeRequest(
            user_id=user_id,
            amount=amount,
            idempotency_key=idempotency_key,
            description=description,
            source=source
        )
        
        try:
            response = self.stub.CreateIncome(request)
            return response
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            raise
    
    def create_expense(self, user_id: str, category_id: str, amount: float,
                       idempotency_key: str, description: Optional[str] = None,
                       allow_negative: bool = False):
        """Создание расхода"""
        request = transaction_service_pb2.CreateExpenseRequest(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            idempotency_key=idempotency_key,
            description=description,
            allow_negative=allow_negative
        )
        
        try:
            response = self.stub.CreateExpense(request)
            return response
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            raise
    
    def get_transaction(self, transaction_id: str):
        """Получение транзакции по ID"""
        request = transaction_service_pb2.GetTransactionRequest(
            transaction_id=transaction_id
        )
        
        response = self.stub.GetTransaction(request)
        return response
    
    def get_user_balance(self, user_id: str):
        """Получение баланса пользователя"""
        request = transaction_service_pb2.GetUserBalanceRequest(
            user_id=user_id
        )
        
        response = self.stub.GetUserBalance(request)
        return response
    
    def get_budget_settings(self, user_id: str):
        """Получение настроек бюджета"""
        request = transaction_service_pb2.GetBudgetSettingsRequest(
            user_id=user_id
        )
        
        response = self.stub.GetBudgetSettings(request)
        return response
    
    def update_budget_settings(self, user_id: str, settings: list):
        """Обновление настроек бюджета"""
        pb_settings = []
        for s in settings:
            pb_settings.append(transaction_service_pb2.BudgetSetting(
                category_id=s['category_id'],
                category_name=s['category_name'],
                percentage=s['percentage'],
                user_id=user_id
            ))
        
        request = transaction_service_pb2.UpdateBudgetSettingsRequest(
            user_id=user_id,
            settings=pb_settings
        )
        
        response = self.stub.UpdateBudgetSettings(request)
        return response
    
    def validate_budget_settings(self, settings: list):
        """Валидация настроек бюджета"""
        pb_settings = []
        for s in settings:
            pb_settings.append(transaction_service_pb2.BudgetSetting(
                category_id=s['category_id'],
                category_name=s['category_name'],
                percentage=s['percentage'],
                user_id="temp"
            ))
        
        request = transaction_service_pb2.ValidateBudgetSettingsRequest(
            settings=pb_settings
        )
        
        response = self.stub.ValidateBudgetSettings(request)
        return response
    
    def get_categories(self, user_id: str):
        """Получение всех категорий пользователя"""
        request = transaction_service_pb2.GetCategoriesRequest(
            user_id=user_id
        )
        
        response = self.stub.GetCategories(request)
        return response
    
    def health_check(self, service: str = "transaction_service"):
        """Проверка здоровья сервиса"""
        request = transaction_service_pb2.HealthCheckRequest(
            service=service
        )
        
        response = self.stub.HealthCheck(request)
        return response
    
    # ========================================
    # SERVER-SIDE STREAMING
    # ========================================
    
    def stream_transactions(self, user_id: str, type_filter=None, status_filter=None, duration=10):
        """
        Стрим транзакций пользователя
        
        Args:
            user_id: ID пользователя
            type_filter: Фильтр по типу (INCOME/EXPENSE)
            status_filter: Фильтр по статусу
            duration: Длительность стрима в секундах
        """
        request = transaction_service_pb2.StreamTransactionsRequest(
            user_id=user_id
        )
        
        if type_filter:
            if type_filter == "INCOME":
                request.type_filter = transaction_service_pb2.TRANSACTION_TYPE_INCOME
            elif type_filter == "EXPENSE":
                request.type_filter = transaction_service_pb2.TRANSACTION_TYPE_EXPENSE
        
        if status_filter:
            if status_filter == "PENDING":
                request.status_filter = transaction_service_pb2.TRANSACTION_STATUS_PENDING
            elif status_filter == "COMPLETED":
                request.status_filter = transaction_service_pb2.TRANSACTION_STATUS_COMPLETED
            elif status_filter == "FAILED":
                request.status_filter = transaction_service_pb2.TRANSACTION_STATUS_FAILED
        
        start_time = time.time()
        
        try:
            for transaction in self.stub.StreamTransactions(request):
                # Прерываем по таймауту
                if time.time() - start_time > duration:
                    break
                
                yield transaction
                
        except grpc.RpcError as e:
            logger.error(f"Stream error: {e.code()} - {e.details()}")
            raise


# ========================================
# DEMO FUNCTIONS
# ========================================

def demo_basic_operations(client):
    """Демонстрация базовых операций"""
    print("\n" + "=" * 60)
    print("📋 ДЕМОНСТРАЦИЯ БАЗОВЫХ ОПЕРАЦИЙ")
    print("=" * 60)
    
    # 1. Health Check
    print("\n1️⃣ Health Check:")
    response = client.health_check()
    status_names = {0: "UNKNOWN", 1: "SERVING", 2: "NOT_SERVING"}
    print(f"   Status: {status_names.get(response.status, 'UNKNOWN')}")
    
    # 2. Get Categories
    print("\n2️⃣ Get Categories:")
    response = client.get_categories("user-001")
    print(f"   Found {len(response.categories)} categories:")
    for cat in response.categories:
        print(f"     • {cat.name} (ID: {cat.id}) - Balance: {cat.balance} руб.")
    
    # 3. Get Budget Settings
    print("\n3️⃣ Get Budget Settings:")
    response = client.get_budget_settings("user-001")
    print(f"   Found {len(response.settings)} settings:")
    for setting in response.settings:
        print(f"     • {setting.category_name}: {setting.percentage}%")
    
    # 4. Create Income
    print("\n4️⃣ Create Income:")
    response = client.create_income(
        user_id="user-001",
        amount=1000.00,
        idempotency_key=f"income_{int(time.time())}",
        description="Зарплата за октябрь",
        source="Зарплата"
    )
    print(f"   ✅ Transaction ID: {response.transaction_id}")
    print(f"   Status: {response.status}")
    print(f"   Distributions:")
    for dist in response.distributions:
        print(f"     • {dist.category_name}: {dist.amount} руб.")
    
    # 5. Get User Balance
    print("\n5️⃣ Get User Balance:")
    response = client.get_user_balance("user-001")
    print(f"   Total Balance: {response.total_balance} руб.")
    print(f"   Category Balances:")
    for cb in response.category_balances:
        print(f"     • {cb.category_name}: {cb.balance} руб.")
    
    # 6. Create Expense
    print("\n6️⃣ Create Expense:")
    response = client.create_expense(
        user_id="user-001",
        category_id="CAT-01",
        amount=200.00,
        idempotency_key=f"expense_{int(time.time())}",
        description="Обед"
    )
    print(f"   ✅ Transaction ID: {response.transaction_id}")
    print(f"   Status: {response.status}")
    print(f"   New Balance: {response.new_balance} руб.")
    
    # 7. Get Transaction
    print("\n7️⃣ Get Transaction:")
    response = client.get_transaction(response.transaction_id)
    if response.found:
        tx = response.transaction
        type_names = {1: "INCOME", 2: "EXPENSE"}
        status_names = {1: "PENDING", 2: "COMPLETED", 3: "FAILED"}
        print(f"   ID: {tx.id}")
        print(f"   Type: {type_names.get(tx.type, 'UNKNOWN')}")
        print(f"   Amount: {tx.amount} руб.")
        print(f"   Status: {status_names.get(tx.status, 'UNKNOWN')}")
        if tx.description:
            print(f"   Description: {tx.description}")
    else:
        print("   ❌ Transaction not found")


def demo_validation(client):
    """Демонстрация валидации"""
    print("\n" + "=" * 60)
    print("📋 ДЕМОНСТРАЦИЯ ВАЛИДАЦИИ")
    print("=" * 60)
    
    # 1. Valid budget settings
    print("\n1️⃣ Valid settings (60% + 40% = 100%):")
    settings = [
        {"category_id": "CAT-01", "category_name": "Покушать", "percentage": 60.0},
        {"category_id": "CAT-02", "category_name": "Накопления", "percentage": 40.0}
    ]
    response = client.validate_budget_settings(settings)
    print(f"   Valid: {response.valid}")
    print(f"   Total: {response.total_percentage}%")
    
    # 2. Invalid budget settings
    print("\n2️⃣ Invalid settings (60% + 50% = 110%):")
    settings = [
        {"category_id": "CAT-01", "category_name": "Покушать", "percentage": 60.0},
        {"category_id": "CAT-02", "category_name": "Накопления", "percentage": 50.0}
    ]
    response = client.validate_budget_settings(settings)
    print(f"   Valid: {response.valid}")
    print(f"   Total: {response.total_percentage}%")
    print(f"   Error: {response.error_message}")


def demo_insufficient_funds(client):
    """Демонстрация ошибки недостаточно средств"""
    print("\n" + "=" * 60)
    print("📋 ДЕМОНСТРАЦИЯ ОШИБКИ: НЕДОСТАТОЧНО СРЕДСТВ")
    print("=" * 60)
    
    try:
        print("\nПопытка списать 10,000 руб. из категории 'Покушать'...")
        response = client.create_expense(
            user_id="user-001",
            category_id="CAT-01",
            amount=10000.00,
            idempotency_key=f"expense_error_{int(time.time())}",
            description="Нереальная трата",
            allow_negative=False
        )
    except grpc.RpcError as e:
        print(f"   ❌ Ошибка: {e.details()}")
        print(f"   Код: {e.code()}")


def demo_streaming(client):
    """Демонстрация server-side streaming"""
    print("\n" + "=" * 60)
    print("📋 ДЕМОНСТРАЦИЯ SERVER-SIDE STREAMING")
    print("=" * 60)
    
    print("\n📡 Стрим транзакций пользователя user-001 (10 секунд)...")
    print("   (создайте новую транзакцию в другом терминале для демонстрации)")
    print("   Нажмите Ctrl+C для остановки\n")
    
    try:
        for tx in client.stream_transactions("user-001", duration=10):
            type_names = {1: "💰 INCOME", 2: "💸 EXPENSE"}
            status_names = {1: "⏳ PENDING", 2: "✅ COMPLETED", 3: "❌ FAILED"}
            print(f"   [{tx.id}] {type_names.get(tx.type, '?')} - {tx.amount} руб. - {status_names.get(tx.status, '?')}")
            
            for dist in tx.distributions:
                print(f"       └─ {dist.category_name}: {dist.amount} руб.")
    
    except KeyboardInterrupt:
        print("\n   Остановка стрима...")


def main():
    """Главная функция"""
    print("=" * 60)
    print("💰 Transaction Service gRPC Client")
    print("   Финучёт «Где мои деньги»")
    print("=" * 60)
    
    client = TransactionServiceClient()
    
    try:
        # Демонстрация базовых операций
        demo_basic_operations(client)
        
        # Демонстрация валидации
        demo_validation(client)
        
        # Демонстрация ошибки
        demo_insufficient_funds(client)
        
        # Демонстрация streaming (опционально, раскомментировать для теста)
        # demo_streaming(client)
        
        print("\n" + "=" * 60)
        print("✅ Все тесты завершены успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        client.close()


if __name__ == '__main__':
    main()