from agency.agent import action


class SayResponseMethods():
    """
    A mixin for converting incoming responses to `say` actions

    NOTE The _message_log will contain both messages
    """

    def handle_return(self, value, original_message_id: str):
        self._receive({
            **self._current_message(),
            "action": {
                "name": "say",
                "args": {
                    "content": str(value),
                }
            },
        })

        # # This was a response to a send()
        # if "value" in message["action"]["args"]:
        #     self.handle_response(
        #         message["action"]["args"]["value"], response_id)
        # # Handle incoming errors
        # elif message["action"]["name"] == "error":
        #     self.handle_error(
        #         message["action"]["args"]["error"], response_id)

    def handle_error(self, error: str, original_message_id: dict):
        self._receive({
            **self._current_message(),
            "action": {
                "name": "say",
                "args": {
                    "content": f"ERROR: {error}",
                }
            },
        })
