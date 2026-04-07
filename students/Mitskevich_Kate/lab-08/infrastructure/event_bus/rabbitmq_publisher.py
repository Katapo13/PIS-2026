import pika
import json
from typing import Dict, Any


class RabbitMQPublisher:
    """Публикатор событий в RabbitMQ"""
    
    def __init__(self, host: str = "rabbitmq", exchange: str = "pso_events"):
        self.host = host
        self.exchange = exchange
        self._connection = None
        self._channel = None
    
    def connect(self):
        """Установка соединения с RabbitMQ"""
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                heartbeat=600,
                blocked_connection_timeout=300
            )
        )
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='topic',
            durable=True
        )
        print(f"Connected to RabbitMQ at {self.host}")
    
    def publish(self, routing_key: str, payload: Dict[str, Any]):
        """Публикация события"""
        if not self._channel:
            self.connect()
        
        message = json.dumps(payload, default=str)
        self._channel.basic_publish(
            exchange=self.exchange,
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent message
                content_type='application/json'
            )
        )
        print(f"Published event: {routing_key}")
    
    def close(self):
        """Закрытие соединения"""
        if self._connection:
            self._connection.close()