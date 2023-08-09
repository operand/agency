import json
import os
import socket
from dataclasses import dataclass
from typing import Dict
import amqp

from kombu import Connection, Exchange, Queue

from agency.agent import Agent
from agency.processors.native_thread_processor import NativeThreadProcessor
from agency.schema import Message
from agency.space import Space
from agency.util import print_warning


@dataclass
class AMQPOptions:
    """
    A class that defines AMQP connection options
    """
    hostname: str = 'localhost'
    port: int = '5672'
    username: str = 'guest'
    password: str = 'guest'
    virtual_host: str = '/'
    use_ssl: bool = False
    heartbeat: float = 60


class AMQPSpace(Space):
    """
    A Space that uses AMQP for message delivery
    """

    BROADCAST_KEY = "__broadcast__"

    def __init__(self, amqp_options: AMQPOptions = None, exchange: str = "agency", processor_class: type = NativeThreadProcessor):
        super().__init__()
        if amqp_options is None:
            amqp_options = self.default_amqp_options()
        self.__kombu_connection_options = {
            'hostname': amqp_options.hostname,
            'port': amqp_options.port,
            'userid': amqp_options.username,
            'password': amqp_options.password,
            'virtual_host': amqp_options.virtual_host,
            'ssl': amqp_options.use_ssl,
            'heartbeat': amqp_options.heartbeat,
        }
        self.__topic_exchange = Exchange(exchange, type="topic", durable=False)
        self.__agent_connections: Dict[str, Connection] = {}

    @classmethod
    def default_amqp_options(cls) -> AMQPOptions:
        """
        Returns a default AMQPOptions object configurable from environment
        variables.
        """
        return AMQPOptions(
            hostname=os.environ.get('AMQP_HOST', 'localhost'),
            port=int(os.environ.get('AMQP_PORT', 5672)),
            username=os.environ.get('AMQP_USERNAME', 'guest'),
            password=os.environ.get('AMQP_PASSWORD', 'guest'),
            virtual_host=os.environ.get('AMQP_VHOST', '/'),
            use_ssl=False,
            heartbeat=60,
        )

    def _connect(self, agent: Agent):
        try:
            # Create a connection
            connection = Connection(**self.__kombu_connection_options)
            connection.connect()
            if not connection.connected:
                raise ConnectionError("Unable to connect to AMQP server")
            self.__agent_connections[agent.id()] = connection

            # Create a queue for direct messages
            direct_queue = Queue(
                f"{agent.id()}-direct",
                exchange=self.__topic_exchange,
                routing_key=agent.id(),
                exclusive=True,
            )
            direct_queue(connection.channel()).declare()

            # Create a separate broadcast queue
            broadcast_queue = Queue(
                f"{agent.id()}-broadcast",
                exchange=self.__topic_exchange,
                routing_key=self.BROADCAST_KEY,
                exclusive=True,
            )
            broadcast_queue(connection.channel()).declare()

            # Define callback for incoming messages
            def _on_message(body, message):
                message.ack()
                message_data = json.loads(body)
                if message_data['to'] == '*' or message_data['to'] == agent.id():
                    agent._receive(message_data)

            # Consume from direct and broadcast queues
            consumer = connection.Consumer(
                [direct_queue, broadcast_queue],
                callbacks=[_on_message],
            )

            # Start the consumer
            consumer.consume()

        except amqp.exceptions.ResourceLocked as e:
            raise ValueError(f"Agent id already exists: '{agent.id()}')")

    def _disconnect(self, agent: Agent):
        connection = self.__agent_connections.pop(agent.id(), None)
        if connection is not None:
            connection.release()

    def _deliver(self, message: Message) -> dict:
        if message['to'] == '*':
            # broadcast
            routing_key = self.BROADCAST_KEY
        else:
            # point to point
            routing_key = message['to']

        with Connection(**self.__kombu_connection_options) as connection:
            with connection.Producer(serializer="json") as producer:
                producer.publish(
                    json.dumps(message),
                    exchange=self.__topic_exchange,
                    routing_key=routing_key,
                )

    def _consume(self, agent: Agent):
        connection = self.__agent_connections[agent.id()]
        connection.heartbeat_check()  # sends heartbeat if necessary
        try:
            connection.drain_events(timeout=0)
        except socket.timeout:
            pass
