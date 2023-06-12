from abc import abstractmethod
from datetime import datetime
from python_agency import util
from python_agency.schema import MessageSchema


class PromptMethods:
    """
    Contains methods for constructing prompts from message logs"""

    def _full_prompt(self):
        """
        Returns the full prompt, including the pre-prompt and the message log"""
        return self._prompt_head() + self._pre_prompt(agent_id=self.id())

    def _message_log_to_list(self, indent=None):
        """Convert an array of message_log entries to a prompt ready list"""
        promptable_list = ""
        for message in self._message_log:
            promptable_list += self._message_line(message, indent)
        return promptable_list

    @abstractmethod
    def _prompt_head(self):
        """
        Returns the "head" of the prompt, the contents up to the pre-prompt
        """
        raise NotImplementedError("Must implement _prompt_head")

    @abstractmethod
    def _pre_prompt(self, agent_id: str, timestamp=util.to_timestamp(datetime.now())):
        """
        Returns the "pre-prompt", the special string sequence that indicates it is
        ones turn to act: e.g. "### Assistant: "
        """
        raise NotImplementedError("Must implement _pre_prompt")

    @abstractmethod
    def _message_line(self, message: MessageSchema, indent=None) -> str:
        """
        Returns a single line for a prompt that represents a previous message
        """
        raise NotImplementedError("Must implement _message_line")
