from abc import ABC, ABCMeta, abstractmethod
from typing import Callable


class Processor(ABC, metaclass=ABCMeta):
    """
    Implements the form of concurrent processing used by a Space instance.

    A processor simply calls the process method frequently. It is intended to
    run concurrently with other processors, so it must do this in a way that
    cooperates with other processor instances.
    """

    def __init__(self, process: Callable):
        self._process = process

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
