import queue
import threading
import time
from typing import Dict, Tuple, Type

from numpy import block

from agency.agent import Agent, QueueProtocol
from agency.schema import Message, validate_message
from agency.space import Space


class _AgentThread():
    def __init__(
            self,
            agent_type: Type[Agent],
            agent_id: str,
            agent_kwargs: Dict,
            inbound_queue: QueueProtocol,
            outbound_queue: QueueProtocol):
        self.__agent_type: Type[Agent] = agent_type
        self.__agent_id: str = agent_id
        self.__agent_kwargs: Dict = agent_kwargs
        self.inbound_queue: QueueProtocol = inbound_queue
        self.outbound_queue: QueueProtocol = outbound_queue

    def start(self):
        def _thread():
            agent = self.__agent_type(
                self.__agent_id,
                outbound_queue=self.outbound_queue,
                **self.__agent_kwargs,
            )
            agent.after_add()
            self.__started.set()
            while not self.__stopping.is_set():
                time.sleep(0.001)
                try:
                    message = self.inbound_queue.get(block=False)
                    agent._receive(message)
                except queue.Empty:
                    pass
            agent.before_remove()

        self.__started = threading.Event()
        self.__stopping = threading.Event()
        self.__thread = threading.Thread(target=_thread)
        self.__thread.start()

        if not self.__started.wait(timeout=10):
            # it couldn't start, force stop the thread and raise an exception
            self.stop()
            raise Exception("Thread could not be started.")

    def stop(self):
        self.__stopping.set()
        self.__thread.join(timeout=10)
        if self.__thread.is_alive():
            raise Exception("Thread could not be stopped.")


class ThreadSpace(Space):
    """A Space implementation that uses the threading module."""

    def __init__(self):
        self.__agent_threads: Dict[str, _AgentThread] = {}
        router_thread = threading.Thread(
            target=self.__router_thread, daemon=True)
        router_thread.start()

    def __router_thread(self):
        """
        A thread that processes outbound messages for all agents, routing them
        to other agents.
        """
        while True:
            time.sleep(0.001)
            for agent_thread in list(self.__agent_threads.values()):
                outbound_queue = agent_thread.outbound_queue
                try:
                    # process one message per agent per loop
                    message = outbound_queue.get(block=False)
                    self._route(message)
                except queue.Empty:
                    pass

    def _route(self, message: Message):
        message = validate_message(message)
        if message["to"] == "*":
            for agent_thread in self.__agent_threads.values():
                agent_thread.inbound_queue.put(message)
        else:
            self.__agent_threads[message["to"]].inbound_queue.put(message)

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs):
        if agent_id in self.__agent_threads.keys():
            raise ValueError(f"Agent id already exists: '{agent_id}'")

        try:
            self.__agent_threads[agent_id] = _AgentThread(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                inbound_queue=queue.Queue(),
                outbound_queue=queue.Queue(),
            )
            self.__agent_threads[agent_id].start()

        except:
            # clean up if an error occurs
            self.remove(agent_id)
            raise

    def remove(self, agent_id: str):
        agent_thread = self.__agent_threads[agent_id]
        agent_thread.stop()
        del self.__agent_threads[agent_id]

    def remove_all(self):
        agent_ids = list(self.__agent_threads.keys())
        for agent_id in agent_ids:
            self.remove(agent_id)
