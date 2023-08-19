from abc import ABC, ABCMeta, abstractmethod
from typing import Protocol

from agency.agent import Agent


class Processor(ABC, metaclass=ABCMeta):
    """
    Implements the form of message queuing and processing used by a Space
    instance for its agents.

    Processor implementations are responsible for maintaining an inbound message
    queue for an Agent and handling incoming messages by invoking the Agent's
    _receive() method.
    """

    def __init__(self, agent: Agent):
        self.agent = agent

    @abstractmethod
    def start(self):
        """
        Starts the processor
        """

    @abstractmethod
    def stop(self):
        """
        Stops the processor
        """
