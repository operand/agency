from agency.agent import ActionError


class SayResponseMethods():
    """
    A mixin for converting incoming responses into `say` actions.

    This is intended to be used within a chat-like context. It will treat the
    `say` action as the primary way to communicate. It assumes all other actions
    are function calls whose responses should be converted into `say` actions.

    NOTE The _message_log will contain both messages
    """

    def handle_action_value(self, value):
        if self.parent_message()["action"]["name"] != "say":
            # This was in response to a function call, convert it to a `say`
            self._receive({
                **self.current_message(),
                "action": {
                    "name": "say",
                    "args": {
                        "content": f"{value}",
                    }
                },
            })

    def handle_action_error(self, error: ActionError):
        # convert errors into a `say` for inspection
        self._receive({
            **self.current_message(),
            "action": {
                "name": "say",
                "args": {
                    "content": f"ERROR: {error}",
                }
            },
        })
