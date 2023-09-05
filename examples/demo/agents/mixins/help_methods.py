from typing import Dict


class HelpMethods():
    """
    A utility mixin for simple discovery of actions upon agent addition

    Adds a member dictionary named `_available_actions`, of the form:
    {
        "agent id": {
            "action name": <action help object>
            ...
        }
    }

    Where the help object above is whatever is returned by the `help` method for
    each action.

    NOTE This does not handle agent removal
    """

    def after_add(self):
        """
        Broadcasts two messages on add:
        1. a message to request actions from other agents
        2. a message to announce its actions to other agents
        """
        self._available_actions: Dict[str, Dict[str, dict]] = {}
        self.send({
            "meta": {
                "id": "request--help",
            },
            "to": "*",
            "action": {
                "name": "help",
            }
        })
        self.send({
            "meta": {
                "request_id": "request--help",
            },
            "to": "*",
            "action": {
                "name": "response",
                "args": {
                    "data": self.help(),
                }
            }
        })

    def handle_action_value(self, value):
        original_message = self._original_message()
        if original_message and original_message["meta"]["id"] == "help_request":
            self._available_actions[self._current_message['from']] = value
        else:
            # this was in response to something else, call the original
            super().handle_action_value(value)
