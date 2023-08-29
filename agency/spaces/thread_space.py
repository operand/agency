import queue
import threading
import time
from typing import Dict, Type

from agency.agent import Agent, RouterProtocol
from agency.schema import Message, validate_message
from agency.space import Space


class _AgentThread():
    def __init__(
            self,
            agent_type: Type[Agent],
            agent_id: str,
            agent_kwargs: Dict,
            message_queue: queue.Queue,
            router: RouterProtocol):
        self.__agent_type: Type[Agent] = agent_type
        self.__agent_id: str = agent_id
        self.__agent_kwargs: Dict = agent_kwargs
        self.__message_queue: queue.Queue = message_queue
        self.__router: RouterProtocol = router
        self.agent: Agent = None  # Set when the thread is started

    def start(self):
        def _thread():
            self.__started.set()
            self.agent = self.__agent_type(
                self.__agent_id,
                router=self.__router,
                **self.__agent_kwargs,
            )
            self.agent.after_add()
            while not self.__stopping.is_set():
                time.sleep(0.001)
                try:
                    message = self.__message_queue.get(block=False)
                    self.agent._receive(message)
                except queue.Empty:
                    pass
            self.agent.before_remove()

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


class _ThreadSpaceRouter():
    def __init__(self, agents: Dict[str, _AgentThread]):
        self.__agent_threads: Dict[str, _AgentThread] = agents

    def route(self, message: Message) -> None:
        message = validate_message(message)
        if message["to"] == "*":
            for agent_thread in self.__agent_threads.values():
                agent_thread.agent._receive(message)
        else:
            self.__agent_threads[message["to"]].agent._receive(message)


class ThreadSpace(Space):
    """
    A Space implementation that uses native threads and queues.
    """

    def __init__(self):
        self.__agent_threads: Dict[str, _AgentThread] = {}
        self.__router: RouterProtocol = _ThreadSpaceRouter(
            self.__agent_threads)

    def add(self, agent_type: Type[Agent], agent_id: str, **agent_kwargs):
        if agent_id in self.__agent_threads.keys():
            raise ValueError(f"Agent id already exists: '{agent_id}'")

        try:
            self.__agent_threads[agent_id] = _AgentThread(
                agent_type=agent_type,
                agent_id=agent_id,
                agent_kwargs=agent_kwargs,
                message_queue=queue.Queue(),
                router=self.__router,
            )
            self.__agent_threads[agent_id].start()

        except:
            # clean up and raise if an error occurs
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
