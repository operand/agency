import json
import os
import queue
import socket
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass

import amqp
import kombu

from agency.logger import log
from agency.queue import Queue
from agency.resources import ResourceManager
from agency.schema import Message
from agency.space import Space

_BROADCAST_KEY = "__broadcast__"

@dataclass
class AMQPOptions:
    """A class that defines AMQP connection options"""
    hostname: str = 'localhost'
    port: int = '5672'
    username: str = 'guest'
    password: str = 'guest'
    virtual_host: str = '/'
    use_ssl: bool = False
    heartbeat: float = 60


class _AMQPQueue(Queue):
    """An AMQP based Queue using the kombu library"""

    def __init__(self, amqp_options: AMQPOptions, exchange_name: str, routing_key: str):
        self.kombu_connection_options = {
            'hostname': amqp_options.hostname,
            'port': amqp_options.port,
            'userid': amqp_options.username,
            'password': amqp_options.password,
            'virtual_host': amqp_options.virtual_host,
            'ssl': amqp_options.use_ssl,
            'heartbeat': amqp_options.heartbeat,
        }
        self.exchange_name: str = exchange_name
        self.routing_key: str = routing_key


class _AMQPInboundQueue(_AMQPQueue):

    def __init__(self, amqp_options: AMQPOptions, exchange_name: str, routing_key: str):
        super().__init__(amqp_options, exchange_name, routing_key)
        self._connection: kombu.Connection = None
        self._exchange: kombu.Exchange = None
        self._direct_queue: kombu.Queue = None
        self._broadcast_queue: kombu.Queue = None
        self._heartbeat_future: Future = None
        self._received_queue: queue.Queue = None
        self._disconnecting: threading.Event = None

    def connect(self):
        log("debug", f"{self.routing_key}: connecting")

        self._received_queue = queue.Queue()

        def _callback(body, amqp_message):
            amqp_message.ack()
            self._received_queue.put(json.loads(body))

        try:
            self._connection = kombu.Connection(
                **self.kombu_connection_options)
            self._connection.connect()
            self._exchange = kombu.Exchange(
                self.exchange_name, 'topic', durable=True)
            self._direct_queue = kombu.Queue(
                self.routing_key,
                exchange=self._exchange,
                routing_key=self.routing_key,
                exclusive=True)
            self._broadcast_queue = kombu.Queue(
                f"{self.routing_key}-broadcast",
                exchange=self._exchange,
                routing_key=_BROADCAST_KEY,
                exclusive=True)
            self._consumer = kombu.Consumer(
                self._connection,
                [self._direct_queue, self._broadcast_queue],
                callbacks=[_callback])
            self._consumer.consume()
        except amqp.exceptions.ResourceLocked:
            raise ValueError(f"Agent '{self.routing_key}' already exists")

        # start heartbeat thread
        def _heartbeat_thread(disconnecting):
            log("debug", f"{self.routing_key}: heartbeat thread starting")
            try:
                while not disconnecting.is_set():
                    try:
                        self._connection.heartbeat_check()
                        self._connection.drain_events(timeout=0.2)
                        time.sleep(0.1)
                    except socket.timeout:
                        pass
            except amqp.exceptions.ConnectionForced:
                log("warning",
                    f"{self.routing_key}: heartbeat connection force closed")
            log("debug", f"{self.routing_key}: heartbeat thread stopped")
        self._disconnecting = threading.Event()
        self._disconnecting.clear()
        self._heartbeat_future = ResourceManager(
        ).thread_pool_executor.submit(_heartbeat_thread, self._disconnecting)

        log("debug", f"{self.routing_key}: connected")

    def disconnect(self):
        log("debug", f"{self.routing_key}: disconnecting")
        if self._disconnecting:
            self._disconnecting.set()
        try:
            if self._heartbeat_future is not None:
                self._heartbeat_future.result(timeout=5)
        finally:
            if self._connection:
                self._connection.close()
        log("debug", f"{self.routing_key}: disconnected")

    def put(self, message: Message):
        raise NotImplementedError("AMQPInboundQueue does not support put")

    def get(self, block: bool = True, timeout: float = None) -> Message:
        message = self._received_queue.get(block=block, timeout=timeout)
        return message


class _AMQPOutboundQueue(_AMQPQueue):

    def __init__(self, amqp_options: AMQPOptions, exchange_name: str, routing_key: str):
        super().__init__(amqp_options, exchange_name, routing_key)
        self._exchange: kombu.Exchange = None

    def connect(self):
        self._exchange = kombu.Exchange(
            self.exchange_name, 'topic', durable=True)
        
    def put(self, message: Message):
        with kombu.Connection(**self.kombu_connection_options) as connection:
            with connection.Producer() as producer:
                if message['to'] == '*':
                    producer.publish(
                        json.dumps(message),
                        exchange=self._exchange,
                        routing_key=_BROADCAST_KEY,
                    )
                else:
                    producer.publish(
                        json.dumps(message),
                        exchange=self._exchange,
                        routing_key=message['to'],
                    )

    def get(self, block: bool = True, timeout: float = None) -> Message:
        raise NotImplementedError("AMQPOutboundQueue does not support get")


class AMQPSpace(Space):
    """
    A Space that uses AMQP for message delivery.

    This Space type is useful for distributing agents across multiple hosts.
    """

    def __init__(self, amqp_options: AMQPOptions = None, exchange_name: str = "agency"):
        super().__init__()
        if amqp_options is None:
            amqp_options = self.__default_amqp_options()
        self.amqp_options = amqp_options
        self.exchange_name = exchange_name

    def __default_amqp_options(self) -> AMQPOptions:
        """
        Returns a default AMQPOptions object configurable from environment
        variables.
        """
        # TODO add support for AMQP_URL
        return AMQPOptions(
            hostname=os.environ.get('AMQP_HOST', 'localhost'),
            port=int(os.environ.get('AMQP_PORT', 5672)),
            username=os.environ.get('AMQP_USERNAME', 'guest'),
            password=os.environ.get('AMQP_PASSWORD', 'guest'),
            virtual_host=os.environ.get('AMQP_VHOST', '/'),
            use_ssl=False,
            heartbeat=60,
        )

    def _create_inbound_queue(self, agent_id) -> Queue:
        return _AMQPInboundQueue(
            amqp_options=self.amqp_options,
            exchange_name=self.exchange_name,
            routing_key=agent_id,
        )

    def _create_outbound_queue(self, agent_id) -> Queue:
        return _AMQPOutboundQueue(
            amqp_options=self.amqp_options,
            exchange_name=self.exchange_name,
            routing_key=agent_id,
        )
