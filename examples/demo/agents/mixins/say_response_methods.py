from agency.agent import action


class SayResponseMethods():
    """
    A mixin for converting incoming `response` and `error` actions to `say`
    actions

    NOTE The _message_log will contain both messages
    """

    @action
    def response(self, data, original_message_id: str):
        self._receive({
            **self._current_message,
            "action": {
                "name": "say",
                "args": {
                    "content": data,
                }
            },
        })

    @action
    def error(self, error: str, original_message_id: dict):
        self._receive({
            **self._current_message,
            "action": {
                "name": "say",
                "args": {
                    "content": f"ERROR: {error}",
                }
            },
        })
