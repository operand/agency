from abc import ABC, ABCMeta, abstractmethod
from typing import List
from agency.agent import Agent
from agency.schema import ActionSchema, MessageSchema
import json
import os
import pika
import threading
import time


class Space(ABC, metaclass=ABCMeta):
    """
    A Space is responsible for:
    - managing the connection lifecycle of its agents
    - routing messages between agents
    """

    @abstractmethod
    def add(self, agent: Agent):
        """
        Adds an agent to the space allowing it to receive messages
        """

    @abstractmethod
    def remove(self, agent: Agent):
        """
        Removes an agent from the space preventing it from receiving messages
        """

    @abstractmethod
    def _route(self, sender: Agent, action: dict) -> dict:
        """
        Routes an action to the appropriate agents on the sender's behalf.
        Returns the message that was sent.
        """


class NativeSpace(Space):
    """
    A Space implementation that uses Python's built-in queue module.
    Suitable for single-process applications and testing.
    """

    def __init__(self):
        self.agents: List[Agent] = []

    def add(self, agent: Agent):
        self.agents.append(agent)
        agent._space = self
        agent._after_add()

    def remove(self, agent: Agent):
        agent._before_remove()
        self.agents.remove(agent)
        agent._space = None

    def _route(self, sender: Agent, action: dict) -> None:
        # Define and validate message
        message = MessageSchema(**{
          **action,
          "from": sender.id(),
        }).dict(by_alias=True)

        broadcast = False
        if 'to' not in message or message['to'] in [None, ""]:
            broadcast = True

        recipients = []
        for agent in self.agents:
            if broadcast or agent.id() == message['to']:
                recipients.append(agent)

        if not broadcast and len(recipients) == 0:
            # route an error back to the sender
            self._route({
                'from': message['to'],
                'to': sender.id(),
                'thoughts': 'An error occurred',
                'action': 'error',
                'args': {
                    'original_message': message,
                    'error': f"\"{message['to']}\" agent not found"
                }
            })
        else:
            # enqueue message for recipients
            for recipient in recipients:
                recipient._receive(message)


class AMQPSpace(Space):
    """
    A Space that uses AMQP (RabbitMQ) for message delivery
    """

    BROADCAST_KEY = "__broadcast__"

    def __init__(self, pika_connection_params: pika.ConnectionParameters = None, exchange: str = "agency"):
        if pika_connection_params is None:
            pika_connection_params = self.default_pika_connection_params()
        self.__connection_params = pika_connection_params
        self.__exchange = exchange
        # set up exchange and broadcast queue
        connection = pika.BlockingConnection(self.__connection_params)
        init_channel = connection.channel()
        init_channel.exchange_declare(
            exchange=self.__exchange, exchange_type='topic')
        init_channel.queue_declare(queue=self.BROADCAST_KEY, auto_delete=True)

    @classmethod
    def default_pika_connection_params(cls) -> pika.ConnectionParameters:
        """
        Returns a default pika connection params object configurable from
        environment variables
        """
        credentials = pika.PlainCredentials(
            os.environ.get('AMQP_USERNAME', 'guest'),
            os.environ.get('AMQP_PASSWORD', 'guest'),
        )
        return pika.ConnectionParameters(
            host=os.environ.get('AMQP_HOST', 'localhost'),
            port=os.environ.get('AMQP_PORT', 5672),
            virtual_host=os.environ.get('AMQP_VHOST', '/'),
            credentials=credentials,
        )

    def add(self, agent: Agent) -> None:
        def _consume_messages():
            # create in/out channels for agent
            out_connection = pika.BlockingConnection(self.__connection_params)
            agent._out_channel = out_connection.channel()
            in_connection = pika.BlockingConnection(self.__connection_params)
            agent._in_channel = in_connection.channel()
            agent._in_channel.queue_declare(queue=agent.id(), auto_delete=True)

            # bind queue to its routing key and broadcast key
            agent._in_channel.queue_bind(exchange=self.__exchange,
                                         queue=agent.id(), routing_key=agent.id())
            agent._in_channel.queue_bind(exchange=self.__exchange,
                                         queue=agent.id(), routing_key=self.BROADCAST_KEY)

            # define callback for incoming messages
            def _on_message(channel, method, properties, body):
                message = MessageSchema(**json.loads(body))
                if message.to == agent.id() or (message.to is None and message.from_field != agent.id()):
                    agent._receive(message)

            # bind callback to queues
            agent._in_channel.basic_consume(
                queue=agent.id(), on_message_callback=_on_message, auto_ack=True)
            agent._in_channel.basic_consume(
                queue=self.BROADCAST_KEY, on_message_callback=_on_message, auto_ack=True)

            # start consuming messages
            agent._space = self
            agent._after_add()
            agent._in_channel.start_consuming()

        threading.Thread(target=_consume_messages).start()
        time.sleep(0.01)  # cooperate

    def remove(self, agent: Agent) -> None:
        agent._before_remove()
        agent._in_channel.connection.add_callback_threadsafe(
            agent._in_channel.connection.close)
        agent._out_channel.connection.add_callback_threadsafe(
            agent._out_channel.connection.close)
        agent._in_channel = None
        agent._out_channel = None
        agent._space = None

    def _route(self, sender: Agent, action: dict) -> dict:
        # Define and validate message
        message = MessageSchema(**{
          **action,
          "from": sender.id(),
        }).dict(by_alias=True)

        routing_key = self.BROADCAST_KEY # broadcast
        if 'to' in message and message['to'] not in [None, ""]:
            routing_key = message['to'] # point to point
            # TODO route an error back to sender if point to point and the recipient is not found
        body = json.dumps(message)
        sender._out_channel.basic_publish(
            exchange=self.__exchange, routing_key=routing_key, body=body)
        return message
