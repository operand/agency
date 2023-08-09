from abc import ABC, ABCMeta, abstractmethod
from typing import Dict
from agency.agent import Agent
from agency.processors.native_thread_processor import NativeThreadProcessor
from agency.schema import Message


class Space(ABC, metaclass=ABCMeta):
    """
    A Space is responsible for:
    - managing the connection lifecycle of its agents
    - routing messages between agents
    """

    def __init__(self, processor_class: type = NativeThreadProcessor):
        self.__processor_class = processor_class
        self.__agent_processors: Dict[str, dict] = {}

    def add(self, agent: Agent):
        """
        Adds an agent to the space allowing it to communicate
        """
        try:
            self._connect(agent)

            def process():
                self._consume(agent)

            processor = self.__processor_class(process)
            self.__agent_processors[agent.id()] = {
                "agent": agent,
                "processor": processor,
            }
            agent._space = self
            agent.after_add()
            processor.start()
        except:
            # clean up and raise if an error occurs
            self.remove(agent)
            raise

    def remove(self, agent: Agent):
        """
        Removes an agent from the space.
        """
        agent.before_remove()
        ap = self.__agent_processors.pop(agent.id(), None)
        if ap is not None:
            ap['processor'].stop()
        self._disconnect(agent)
        agent._space = None

    def remove_all(self):
        """
        Removes all agents added through this space instance.
        """
        agents = [ap['agent'] for ap in self.__agent_processors.values()]
        for agent in agents:
            self.remove(agent)
        self.__agent_processors.clear()

    def _route(self, message: Message) -> None:
        """
        Validates and delivers a message to the appropriate agents
        """
        message = Message(**message).dict(
            by_alias=True,
            exclude_unset=True,
        )
        self._deliver(message)

    @abstractmethod
    def _connect(self, agent: Agent):
        """
        Connects an agent to the space.

        This method is called when adding an agent to the space. It should
        establish a queue or similar data structure for the agent to receive
        messages.

        Raises:
            ValueError: If the agent ID is already in use
        """

    @abstractmethod
    def _disconnect(self, agent: Agent):
        """
        Disconnects an agent from the space.

        This method is called when removing an agent from the space. It should
        close the queue or similar data structure for the agent.
        """

    @abstractmethod
    def _deliver(self, message: Message) -> None:
        """
        Delivers a message to the appropriate agents.

        This method is called whenever an agent sends a message. It should place
        that message on some type of queue associated with the agent id in the
        message['to'] field.
        """

    @abstractmethod
    def _consume(self, agent: Agent):
        """
        Consumes messages from an agent's queue.

        This method may be called many times per second. It should check for
        messages on the agent's queue and pass any to agent._receive(). If no
        messages are present it should return immediately rather than block.
        """
