from abc import ABC, ABCMeta, abstractmethod
from typing import Type
from agency.agent import Agent
from agency.schema import Message


class Space(ABC, metaclass=ABCMeta):
    """
    A Space is responsible for:
    - managing the lifecycle of its agents as they are added/removed
    - routing messages between agents
    """

    @abstractmethod
    def add(self, agent_type: Type[Agent], agent_id: str, **kwargs) -> Agent:
        """
        Adds an agent to the space allowing it to communicate.

        Args:
            agent_type: The type of agent to add
            agent_id: The id of the agent to add

        Returns:
            Agent: The agent that was added

        Raises:
            ValueError: If the agent ID is already in use
        """

    @abstractmethod
    def remove(self, agent_id: str):
        """
        Removes an agent from the space.

        This method can only remove an agent instance added from the same space
        instance where it was added. In other words, a Space instance cannot
        remove an agent that it did not add.

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
