from agency import util
from agency.agent import ACCESS_PERMITTED, access_policy


class HelpMethods():
    """
    A utility mixin containing:
    - default implementations of return/error actions for converting into
      "say" messages.
    - _after_add callback for sending a help message on agent addition,
      available as self._available_actions
    """

    def _after_add(self):
        """
        Sends two messages on add:
        1. a broadcast to announce its actions to other agents
        2. a help message to the space to receive available actions

        This allows all agents to auto-discover actions upon addition.
        NOTE this does not handle agent removal
        """
        self._available_actions = []
        self._send({
            "thoughts": "Here is a list of actions you can take on me.",
            "action": "return",
            "args": {
                "original_message": {
                    "action": "help",
                },
                "return_value": self._help(),
            }
        })
        self._send({
            "thoughts": "I should see what actions are available.",
            "action": "help",
            "args": {},
        })

    @access_policy(ACCESS_PERMITTED)
    def _action__return(self, original_message: dict, return_value):
        if original_message['action'] == "help":
            # add to the list of available actions
            for action_help in return_value:
                if action_help not in self._available_actions:
                    self._available_actions.append(action_help)
        else:
            # convert to a "say"
            self._receive({
                "from": self._current_message['from'],
                "to": self._current_message['to'],
                "thoughts": f"A value was returned for your action '{original_message['action']}'",
                "action": "say",
                "args": {
                    "content": return_value.__str__(),
                },
            })

    @access_policy(ACCESS_PERMITTED)
    def _action__error(self, original_message: dict, error: str):
        self._receive({
            "from": self._current_message['from'],
            "to": self._current_message['to'],
            "thoughts": "An error occurred",
            "action": "say",
            "args": {
                "content": f"ERROR: {error}",
            },
        })
