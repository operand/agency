import json
import multiprocessing
import os
import queue
import socket
import threading
import time
import traceback
from dataclasses import dataclass
from multiprocessing import Event, Process
from typing import Dict, Type

from amqp import ResourceLocked
from kombu import Connection, Exchange, Queue

from agency.agent import Agent
from agency.logger import log
from agency.schema import Message, validate_message
from agency.space import Space


class _AgentAMQPProcess():
    def __init__(
        self,
        agent_type: Type[Agent],
        agent_id: str,
        agent_kwargs: Dict,
        kombu_connection_options: Dict,
        exchange_name: str,
        outbound_queue: multiprocessing.Queue,
    ):
        self.agent_type: Type[Agent] = agent_type
        self.agent_id: str = agent_id
        self.agent_kwargs: Dict = agent_kwargs
        self.kombu_connection_options: Dict = kombu_connection_options
        self.exchange_name: str = exchange_name
        self.outbound_queue: multiprocessing.Queue = outbound_queue

    def start(self):
        self.__started = Event()
        self.__stopping = Event()
        error_queue = multiprocessing.Queue()
        self.__process = Process(
            target=self._process,
            args=(
                self.agent_type,
                self.agent_id,
                self.agent_kwargs,
                self.kombu_connection_options,
                self.exchange_name,
                self.outbound_queue,
                self.__started,
                self.__stopping,
                error_queue,
            )
        )
        self.__process.start()

        if not self.__started.wait(timeout=10):
            self.stop()
            try:
                error = error_queue.get(block=False)
                raise error
            except queue.Empty:
                raise Exception("Process could not be started.")

    def stop(self):
        self.__stopping.set()
        if self.__process.is_alive():
            self.__process.join(timeout=10)
        if self.__process.is_alive():
            raise Exception("Process could not be stopped.")

    def _process(self,
                 agent_type,
                 agent_id,
                 agent_kwargs,
                 kombu_connection_options,
                 exchange_name,
                 outbound_queue,
                 started,
                 stopping,
                 error_queue):

        try:
            # Create a connection and Exchange
            exchange: Exchange = Exchange(
                exchange_name,
                type='topic',
                durable=False,
            )
            connection = Connection(**kombu_connection_options)
            connection.connect()
            if not connection.connected:
                raise ConnectionError("Unable to connect to AMQP server")

            # Create a queue for direct messages
            direct_queue = Queue(
                f"{agent_id}-direct",
                exchange=exchange,
                routing_key=agent_id,
                exclusive=True,
            )
            direct_queue(connection.channel()).declare()

            # Create a separate broadcast queue
            broadcast_queue = Queue(
                f"{agent_id}-broadcast",
                exchange=exchange,
                routing_key=AMQPSpace._BROADCAST_KEY,
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

            # Create agent
            agent: Agent = agent_type(
                agent_id,
                outbound_queue=outbound_queue,
                **agent_kwargs,
            )

            # Start loop
            agent.after_add()
            log("info", f"{agent.id()} added to space")
            agent._is_processing = True
            started.set()
            while not stopping.is_set():
                time.sleep(0.001)
                connection.heartbeat_check()  # sends heartbeat if necessary
                try:
                    connection.drain_events(timeout=0.001)
                except socket.timeout:
                    pass
        except ResourceLocked:
            error_queue.put(
                ValueError(f"Agent id already exists: '{agent_id}'"))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            log("error", f"{agent_id} process failed with exception",
                traceback.format_exc())
            error_queue.put(e)
        finally:
            agent._is_processing = False
            agent.before_remove()
            connection.release()
            log("info", f"{agent.id()} removed from space")


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
    A Space that uses AMQP for message delivery.

    This Space type is useful for distributing agents across multiple hosts.

    AMQPSpace uses multiprocessing for parallelism when multiple agents are
    added to the same instance.
    """

    _BROADCAST_KEY = "__broadcast__"

    def __init__(self, amqp_options: AMQPOptions = None, exchange_name: str = "agency"):
        if amqp_options is None:
            amqp_options = self.__default_amqp_options()
        self.__kombu_connection_options = {
            'hostname': amqp_options.hostname,
            'port': amqp_options.port,
            'userid': amqp_options.username,
            'password': amqp_options.password,
            'virtual_host': amqp_options.virtual_host,
            'ssl': amqp_options.use_ssl,
            'heartbeat': amqp_options.heartbeat,
        }
        self.__exchange_name: str = exchange_name
        self.__exchange: Exchange = Exchange(
            self.__exchange_name,
            type='topic',
            durable=False,
        )
        self.__agent_processes: Dict[str, _AgentAMQPProcess] = {}
        router_thread = threading.Thread(
            target=self.__router_thread, daemon=True)
        router_thread.start()

    def __router_thread(self):
        """Processes and routes outbound messages for all agents"""
        while True:
            time.sleep(0.001)
            for agent_process in list(self.__agent_processes.values()):
                outbound_queue = agent_process.outbound_queue
                try:
                    # process one message per agent per loop
                    message = outbound_queue.get(block=False)
                    self._route(message)
                except queue.Empty:
                    pass

    def _route(self, message: Message):
        message = validate_message(message)

        if message['to'] == '*':
            # broadcast
            routing_key = self._BROADCAST_KEY
        else:
            # point to point
            routing_key = message['to']

        with Connection(**self.__kombu_connection_options) as connection:
            with connection.Producer(serializer="json") as producer:
                producer.publish(
                    json.dumps(message),
                    exchange=self.__exchange,
                    routing_key=routing_key)

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs) -> Agent:
        try:
            self.__agent_processes[agent_id] = _AgentAMQPProcess(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                kombu_connection_options=self.__kombu_connection_options,
                exchange_name=self.__exchange_name,
                outbound_queue=multiprocessing.Queue(),
            )
            self.__agent_processes[agent_id].start()

        except:
            # clean up if an error occurs
            self.remove(agent_id)
            raise

    def remove(self, agent_id: str):
        agent_process = self.__agent_processes[agent_id]
        agent_process.stop()
        del self.__agent_processes[agent_id]

    def remove_all(self):
        agent_ids = list(self.__agent_processes.keys())
        for agent_id in agent_ids:
            self.remove(agent_id)

    def __default_amqp_options(self) -> AMQPOptions:
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
