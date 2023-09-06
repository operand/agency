from abc import ABC, ABCMeta, abstractmethod
from typing import Type
from agency.agent import Agent


class Space(ABC, metaclass=ABCMeta):
    """
    Space implementations are responsible for
    - Managing the lifecycle of agent instances
    - Ensuring communication between agents
    """

    @abstractmethod
    def add(self, agent_type: Type[Agent], agent_id: str, **kwargs):
        """
        Adds an agent to the space allowing it to communicate.

        Keyword arguments are passed to the agent's constructor.

        Args:
            agent_type: The type of agent to add
            agent_id: The id of the agent to add

        Raises:
            ValueError: If the agent ID is already in use
        """

    @abstractmethod
    def remove(self, agent_id: str):
        """
        Removes an agent from the space by id.

        This method cannot remove an agent instance added from a different space
        instance. In other words, a space instance cannot remove an agent that
        it did not add.

        Args:
            agent_id: The id of the agent to remove

        Raises:
            ValueError: If the agent is not present in the space
        """

    @abstractmethod
    def remove_all(self):
        """
        Removes all agents added through this space instance.
        """
