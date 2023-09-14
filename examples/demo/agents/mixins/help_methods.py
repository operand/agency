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
                "id": "help_request",
            },
            "to": "*",
            "action": {
                "name": "help",
            }
        })
        self.send({
            "meta": {
                "parent_id": "help_request",
            },
            "to": "*",
            "action": {
                "name": "[response]",
                "args": {
                    "value": self.help(),
                }
            }
        })

    def handle_action_value(self, value):
        current_message = self.current_message()
        if current_message["meta"].get("parent_id", None) == "help_request":
            self._available_actions[current_message["from"]] = value
        else:
            # this was in response to something else, call the original
            super().handle_action_value(value)
