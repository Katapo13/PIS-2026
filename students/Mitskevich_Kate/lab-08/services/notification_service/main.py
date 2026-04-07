from fastapi import FastAPI
import aio_pika
import json
import smtplib
from email.mime.text import MIMEText

app = FastAPI(title="Notification Service", port=8004)


async def consume_events():
    """Подписка на события из RabbitMQ"""
    connection = await aio_pika.connect_robust("amqp://guest:guest@rabbitmq/")
    
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("notification_queue", durable=True)
        
        await queue.bind("pso_events", routing_key="TransactionCompleted")
        await queue.bind("pso_events", routing_key="BudgetWarning")
        
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                event = json.loads(message.body.decode())
                
                if message.routing_key == "TransactionCompleted":
                    await send_transaction_notification(event)
                elif message.routing_key == "BudgetWarning":
                    await send_budget_warning(event)
        
        await queue.consume(on_message)
        await asyncio.Future()


async def send_transaction_notification(event: dict):
    """Отправка уведомления о транзакции"""
    user_email = await get_user_email(event["user_id"])
    
    subject = f"Новая транзакция: {event['transaction_type']}"
    body = f"""
    Уважаемый пользователь!
    
    Зарегистрирована новая транзакция:
    - Тип: {event['transaction_type']}
    - Сумма: {event['amount']} руб.
    - Дата: {event['created_at']}
    
    С уважением,
    Система «Где мои деньги»
    """
    
    await send_email(user_email, subject, body)


async def send_budget_warning(event: dict):
    """Отправка предупреждения о бюджете"""
    user_email = await get_user_email(event["user_id"])
    
    subject = f"⚠️ Предупреждение: превышение бюджета в категории «{event['category_name']}»"
    body = f"""
    Уважаемый пользователь!
    
    Вы потратили {event['budget_usage']:.1f}% бюджета в категории «{event['category_name']}».
    
    Рекомендуем пересмотреть расходы в этой категории.
    
    Текущий баланс: {event['current_balance']} руб.
    
    С уважением,
    Система «Где мои деньги»
    """
    
    await send_email(user_email, subject, body)


@app.on_event("startup")
async def startup():
    asyncio.create_task(consume_events())