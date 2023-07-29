from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from typing import List
from agency import util
from agency.schema import Message


class PromptMethods(ABC, metaclass=ABCMeta):
    """
    A mixin containing utility methods for constructing prompts from the message
    log
    """

    def _full_prompt(self):
        """
        Returns the full prompt, including the pre-prompt and the message log
        """
        return self._prompt_head() + self._pre_prompt(agent_id=self.id())

    def _message_log_to_list(self, message_log: List[Message]) -> str:
        """Convert an array of message_log entries to a prompt ready list"""
        promptable_list = ""
        for message in message_log:
            promptable_list += self._message_line(message)
        return promptable_list

    @abstractmethod
    def _prompt_head(self):
        """
        Returns the "head" of the prompt, the contents up to the pre-prompt
        """

    @abstractmethod
    def _pre_prompt(self, agent_id: str, timestamp=util.to_timestamp(datetime.now())):
        """
        Returns the "pre-prompt", the special string sequence that indicates it is
        ones turn to act: e.g. "### Assistant: "
        """

    @abstractmethod
    def _message_line(self, message: Message) -> str:
        """
        Returns a single line for a prompt that represents a previous message
        """
