# import inspect  # install micropython_inspect
import re

# access keys
ACCESS = "access"
ACCESS_PERMITTED = "permitted"
ACCESS_DENIED = "denied"
ACCESS_REQUESTED = "requested"

# Special action name for responses
_RESPONSE_ACTION_NAME = "[response]"


_function_access_policies = {}  # work with action decorator

def action(*args, **kwargs):
    def decorator(method):
        _function_access_policies[method.__name__] = {
            "name": method.__name__,
            "access_policy": ACCESS_PERMITTED,
            "help": None,
            # **kwargs, # not supported by micropython
        }
        _function_access_policies[method.__name__].update(kwargs)

        return method

    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])  # The decorator was used without parentheses
    else:
        return decorator  # The decorator was used with parentheses

class ActionError(Exception):
    """Raised from the request() method if the action responds with an error"""


class UAgent:
    """
    An Actor that may represent an AI agent, computing system, or human user
    """

    def __init__(self, id: str, receive_own_broadcasts: bool = True) -> None:
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError('id cannot start with "amq."')
        if id == "*":
            raise ValueError('id cannot be "*"')
        self.__id: str = id
        self.__receive_own_broadcasts = receive_own_broadcasts
        self._space = None  # set by Space when added
        self._message_log = []  # stores all messages

    def id(self) -> str:
        """
        Returns the id of this agent
        """
        return self.__id

    def send(self, message: dict):
        """
        Sends (out) an message
        """
        message["from"] = self.id()
        self._message_log.append(message)
        self._space._route(message=message)

    def _receive(self, message: dict):
        """
        Receives and processes an incoming message
        """
        if (
            not self.__receive_own_broadcasts
            and message["from"] == self.id()
            and message["to"] == "*"
        ):
            return

        # Record message and commit action
        self._message_log.append(message)

        if message["action"]["name"] == _RESPONSE_ACTION_NAME:
            if "value" in message["action"]["args"]:
                handler_callback = self.handle_action_value
                arg = message["action"]["args"]["value"]
            elif "error" in message["action"]["args"]:
                handler_callback = self.handle_action_error
                arg = ActionError(message["action"]["args"]["error"])
            else:
                raise RuntimeError("Unknown action response")
            handler_callback(arg)
        else:
            try:
                self.__commit(message)
            except Exception as e:
                # Here we handle exceptions that occur while committing an action,
                # including PermissionError's from access denial, by reporting the
                # error back to the sender.
                request_id = message.get("meta", {}).get("request_id")
                response_id = request_id or message.get("meta", {}).get("id")
                self.send({
                    "meta": {
                        "response_id": response_id
                    },
                    "to": message['from'],
                    "from": self.id(),
                    "action": {
                        "name": _RESPONSE_ACTION_NAME,
                        "args": {
                            "error": f"{e.__class__.__name__}: {e}"
                            # "error": f"{e}"
                        }
                    }
                })

    def __commit(self, message: dict):
        """
        Invokes action if permitted otherwise raises PermissionError
        """
        # Check if the action method exists
        action_method = None
        try:
            # action_method = self.__action_method(message["action"]["name"])
            action_method = getattr(self, f"{message['action']['name']}")
            assert (
                message["action"]["name"] in _function_access_policies
            )  # security check
        except KeyError:
            # the action was not found
            if message["to"] == self.id():
                # if it was point to point, raise an error
                raise AttributeError(
                    f"\"{message['action']['name']}\" not found on \"{self.id()}\""
                )
            else:
                # broadcasts will not raise an error
                return

        self.before_action(message)

        return_value = None
        error = None
        try:
            # Check if the action is permitted
            if self.__permitted(message):
                # Invoke the action method
                # (set _current_message so that it can be used by the action)
                self._current_message = message
                return_value = action_method(**message["action"]["args"])
                self._current_message = None

                # The return value if any, from an action method is sent back to
                # the sender as a "response" action.
                request_id = message.get("meta", {}).get("request_id")
                response_id = request_id or message.get("meta", {}).get("id")
                if request_id or return_value is not None:
                    self.send({
                        "meta": {
                            "response_id": response_id
                        },
                        "to": message['from'],
                        "action": {
                            "name": _RESPONSE_ACTION_NAME,
                            "args": {
                                "value": return_value,
                            }
                        }
                    })
            else:
                raise PermissionError(
                    f"\"{self.id()}.{message['action']['name']}\" not permitted"
                )
        except Exception as e:
            error = e  # save the error for after_action
            raise
        finally:
            self.after_action(message, return_value, error)

    def __permitted(self, message: dict) -> bool:
        """
        Checks whether the action represented by the message is allowed
        """
        policy = _function_access_policies[f"{message['action']['name']}"][
            "access_policy"
        ]
        if policy == ACCESS_PERMITTED:
            return True
        elif policy == ACCESS_DENIED:
            return False
        elif policy == ACCESS_REQUESTED:
            return self.request_permission(message)
        else:
            raise Exception(
                f"Invalid access policy for method: {message['action']}, got '{policy}'"
            )

    @action
    def help(self, action_name: str = None) -> list:
        """
        Returns a list of actions on this agent.

        If action_name is passed, returns a list with only that action.
        If no action_name is passed, returns all actions.

        Args:
            action_name: (Optional) The name of an action to request help for

        Returns:
            A list of actions
        """
        return self._help(action_name)

    def after_add(self):
        """
        Called after the agent is added to a space, but before it begins
        processing incoming messages.

        The agent may send messages during this callback using the send()
        method, but may not use the request() method since it relies on
        processing incoming messages.
        """

    def before_remove(self):
        """
        Called before the agent is removed from a space, after it has finished
        processing incoming messages.

        The agent may send final messages during this callback using the send()
        method, but may not use the request() method since it relies on
        processing incoming messages.
        """

    def before_action(self, message: dict):
        """
        Called before every action.

        This method will only be called if the action exists and is permitted.

        Args:
            message: The received message that contains the action
        """

    def after_action(self, message: dict, return_value: str, error: str):
        """
        Called after every action, regardless of whether an error occurred.

        Args:
            message: The message which invoked the action
            return_value: The return value from the action
            error: The error from the action if any
        """

    def request_permission(self, proposed_message: dict) -> bool:
        """
        Receives a proposed action message and presents it to the agent for
        review.

        Args:
            proposed_message: The proposed action message

        Returns:
            True if access should be permitted
        """
        raise NotImplementedError(
            f"You must implement {self.__class__.__name__}.request_permission() to use ACCESS_REQUESTED")

    def handle_action_value(self, value):
        """
        Receives a return value from a previous action.

        This method receives return values from actions invoked by the send()
        method. It is not called when using the request() method, which returns
        the value directly.

        To inspect the full response message, use current_message().

        To inspect the original message, use original_message(). Note that the
        original message must define the meta.id field or original_message()
        will return None.

        Args:
            value:
                The return value
        """

    def handle_action_error(self, error: ActionError):
        """
        Receives an error from a previous action.

        This method receives errors from actions invoked by the send() method.
        It is not called when using the request() method, which raises an error
        directly.

        To inspect the full response message, use current_message().

        To inspect the original message, use original_message(). Note that the
        original message must define the meta.id field or original_message()
        will return None.

        Args:
            error: The error
        """