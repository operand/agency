import json
import os
import socket
import threading
import time
from dataclasses import dataclass

from amqp import ChannelError
from kombu import Connection, Exchange, Queue

from agency.agent import Agent
from agency.schema import MessageSchema
from agency.space import Space


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
    A Space that uses AMQP (RabbitMQ) for message delivery
    """

    BROADCAST_KEY = "__broadcast__"

    def __init__(self, amqp_options: AMQPOptions = None, exchange: str = "agency"):
        if amqp_options is None:
            amqp_options = self.default_amqp_options()
        # map AMQPOptions for kombu
        self.__kombu_connection_options = {
            'hostname': amqp_options.hostname,
            'port': amqp_options.port,
            'userid': amqp_options.username,
            'password': amqp_options.password,
            'virtual_host': amqp_options.virtual_host,
            'ssl': amqp_options.use_ssl,
            'heartbeat': amqp_options.heartbeat,
        }
        # setup topic exchange
        self.__topic_exchange = Exchange(exchange, type="topic", durable=False)

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

    def add(self, agent: Agent) -> None:
        # define callback for incoming messages
        def _on_message(body, message):
            message.ack()
            message_data = json.loads(body)
            broadcast = 'to' not in message_data or message_data['to'] in [
                None, ""]
            if broadcast and message_data['from'] != agent.id() \
               or not broadcast and message_data['to'] == agent.id():
                agent._receive(message_data)

        def _consume_messages():
            with Connection(**self.__kombu_connection_options) as connection:
                agent_qid = self.__agent_queue_id(agent)

                # Create a non-exclusive named queue on the agent id,
                # auto-deleted when the last instance disconnects. This queue is
                # not used for messaging but for determining whether an agent
                # has any remaining open connections. I'm not fond of this
                # approach but it works decently for now.
                id_queue = Queue(
                    agent.id(),
                    exchange=self.__topic_exchange,
                    routing_key='', # shouldn't receive messages
                    auto_delete=True
                )
                id_queue(connection.channel()).declare()

                # Create a queue for direct messages
                direct_queue = Queue(
                    f"{agent_qid}-direct",
                    exchange=self.__topic_exchange,
                    routing_key=agent.id(),
                    exclusive=True,
                )
                direct_queue(connection.channel()).declare()

                # Create a separate broadcast queue for each agent
                broadcast_queue = Queue(
                    f"{agent_qid}-broadcast",
                    exchange=self.__topic_exchange,
                    routing_key=self.BROADCAST_KEY,
                    exclusive=True,
                )
                broadcast_queue(connection.channel()).declare()

                # Consume from direct and broadcast queues. The id_queue is
                # included for tracking connections but does not receive
                # messages.
                with connection.Consumer(
                    [id_queue, direct_queue, broadcast_queue],
                    callbacks=[_on_message],
                ):
                    agent._space = self
                    agent._thread_started.set()
                    while not agent._thread_stopping.is_set():
                        time.sleep(0.01)
                        connection.heartbeat_check()  # sends heartbeat if necessary
                        try:
                            connection.drain_events(timeout=0.01)
                        except socket.timeout:
                            pass

            agent._thread_stopped.set()

        # start thread
        threading.Thread(target=_consume_messages).start()
        if not agent._thread_started.wait(timeout=5):
            raise Exception(
                f"Agent {agent.id()} could not be added. Thread timeout.")
        else:
            agent._after_add()

    def remove(self, agent: Agent) -> None:
        agent._before_remove()
        agent._thread_stopping.set()
        agent._thread_stopped.wait()
        agent._space = None

    def _route(self, sender: Agent, action: dict) -> dict:
        # Define and validate message
        message = MessageSchema(**{
          **action,
          "from": sender.id(),
        }).dict(by_alias=True)

        if 'to' in message and message['to'] not in [None, ""]:
            # point to point
            routing_key = message['to']
        else:
            # broadcast
            routing_key = self.BROADCAST_KEY

        sender._message_log.append(message)
        if routing_key == self.BROADCAST_KEY or self._check_queue_exists(routing_key):
            self.__publish(routing_key, message)
        else:
            if routing_key == sender.id():
                # if the routing key equals the sender id, we have a problem.
                # the sender's own queue doesn't exist so we can't route an
                # error back. raise an exception to prevent an infinite loop.
                raise Exception("Cannot route error. Missing sender queue.")
            else:
                # send an error back
                error_message = {
                    'from': sender.id(),
                    'to': sender.id(),
                    'thoughts': 'An error occurred',
                    'action': 'error',
                    'args': {
                        'original_message': message,
                        'error': f"\"{message['to']}\" not found",
                    }
                }
                self.__publish(sender.id(), error_message)

    def __agent_queue_id(self, agent: Agent):
        """
        Returns a unique queue id for the agent instance based on:
        - the agent id
        - the hostname
        - the process id
        - the agent object id
        """
        return f"{agent.id()}-{socket.gethostname()}-{os.getpid()}-{id(agent)}"

    def __publish(self, routing_key: str, message: dict):
        with Connection(**self.__kombu_connection_options) as connection:
            with connection.Producer(serializer="json") as producer:
                producer.publish(
                    json.dumps(message),
                    exchange=self.__topic_exchange,
                    routing_key=routing_key,
                )

    def _check_queue_exists(self, queue_name):
        with Connection(**self.__kombu_connection_options) as connection:
            try:
                with connection.channel() as channel:
                    channel.queue_declare(
                        queue=queue_name,
                        passive=True,
                    )
                return True
            except ChannelError:
                return False
