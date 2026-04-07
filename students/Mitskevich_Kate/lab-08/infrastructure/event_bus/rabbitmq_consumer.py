import pika
import json
from typing import Callable, Dict, Any


class RabbitMQConsumer:
    """Подписчик на события из RabbitMQ"""
    
    def __init__(self, host: str = "rabbitmq", exchange: str = "pso_events"):
        self.host = host
        self.exchange = exchange
        self._connection = None
        self._channel = None
    
    def connect(self, queue_name: str, routing_keys: list):
        """Установка соединения и подписка"""
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host)
        )
        self._channel = self._connection.channel()
        
        # Создание exchange
        self._channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='topic',
            durable=True
        )
        
        # Создание очереди
        result = self._channel.queue_declare(
            queue=queue_name,
            durable=True,
            exclusive=False
        )
        queue_name = result.method.queue
        
        # Привязка к routing keys
        for routing_key in routing_keys:
            self._channel.queue_bind(
                exchange=self.exchange,
                queue=queue_name,
                routing_key=routing_key
            )
            print(f"Bound to {routing_key}")
        
        return queue_name
    
    def consume(self, queue_name: str, callback: Callable):
        """Начало прослушивания очереди"""
        self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        print(f"Listening for events on queue: {queue_name}")
        self._channel.start_consuming()
    
    def close(self):
        """Закрытие соединения"""
        if self._connection:
            self._connection.close()