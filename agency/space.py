from abc import ABC, ABCMeta, abstractmethod
from agency.agent import Agent


class Space(ABC, metaclass=ABCMeta):
    """
    A Space is responsible for:
    - managing the connection lifecycle of its agents
    - routing messages between agents
    """

    @abstractmethod
    def add(self, agent: Agent) -> None:
        """
        Adds an agent to the space allowing it to receive messages
        """

    @abstractmethod
    def remove(self, agent: Agent) -> None:
        """
        Removes an agent from the space preventing it from receiving messages
        """

    @abstractmethod
    def _route(self, sender: Agent, action: dict) -> None:
        """
        Routes an action to the appropriate agents on the sender's behalf.
        """
