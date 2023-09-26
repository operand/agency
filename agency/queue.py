from abc import ABC, ABCMeta, abstractmethod

from agency.schema import Message


class Queue(ABC, metaclass=ABCMeta):
    """
    Encapsulates a queue intended to be used for communication
    """

    def connect(self) -> None:
        """
        Connects to the queue

        This method is called before the queue is first accessed and establishes
        a connection if necessary.
        """

    def disconnect(self) -> None:
        """
        Disconnects from the queue

        This method is called after the queue will no longer be accessed and
        closes a connection if necessary.
        """

    @abstractmethod
    def put(self, message: Message):
        """
        Put a message onto the queue for sending

        Args:
            message: The message
        """

    @abstractmethod
    def get(self, block: bool = True, timeout: float = None) -> Message:
        """
        Get the next message from the queue

        Args:
            block: Whether to block
            timeout: The timeout

        Returns:
            The next message

        Raises:
            queue.Empty: If there are no messages
        """
