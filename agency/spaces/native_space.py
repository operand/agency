import queue
from typing import Dict
from agency.agent import Agent
from agency.processors.native_thread_processor import NativeThreadProcessor
from agency.schema import Message
from agency.space import Space


class NativeSpace(Space):
    """
    A Space implementation that uses Python's built-in queue module.
    Suitable for single-process applications and testing.
    """

    def __init__(self, processor_class: type = NativeThreadProcessor):
        super().__init__(processor_class=processor_class)
        self.__agent_queues: Dict[str, queue.Queue] = {}

    def _connect(self, agent: Agent):
        if agent.id() in self.__agent_queues.keys():
            raise ValueError(f"Agent id already exists: '{agent.id()}')")
        self.__agent_queues[agent.id()] = queue.Queue()

    def _disconnect(self, agent: Agent):
        del self.__agent_queues[agent.id()]

    def _deliver(self, message: Message) -> None:
        for agent_id in self.__agent_queues.keys():
            if message['to'] == '*' or message['to'] == agent_id:
                self.__agent_queues[agent_id].put(message)

    def _consume(self, agent: Agent):
        agent_queue = self.__agent_queues[agent.id()]
        try:
            message = agent_queue.get(block=False)
            if message['to'] == '*' or message['to'] == agent.id():
                agent._receive(message)
        except queue.Empty:
            pass
