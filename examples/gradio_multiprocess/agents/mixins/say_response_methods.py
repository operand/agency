from agency.agent import ActionError


class SayResponseMethods():
    """
    A mixin for converting incoming responses to `say` actions

    NOTE The _message_log will contain both messages
    """

    def handle_action_value(self, value):
        self._receive({
            **self.current_message(),
            "action": {
                "name": "say",
                "args": {
                    "content": str(value),
                }
            },
        })

    def handle_action_error(self, error: ActionError):
        self._receive({
            **self.current_message(),
            "action": {
                "name": "say",
                "args": {
                    "content": f"ERROR: {error}",
                }
            },
        })
