# import inspect  # install micropython_inspect
import re

# access keys
ACCESS = "access"
ACCESS_PERMITTED = "permitted"
ACCESS_DENIED = "denied"
ACCESS_REQUESTED = "requested"


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

        try:
            # Record message and commit action
            self._message_log.append(message)
            self.__commit(message)
        except Exception as e:
            # Here we handle exceptions that occur while committing an action,
            # including PermissionError's from access denial, by reporting the
            # error back to the sender.
            self.send(
                {
                    "to": message["from"],
                    "from": self.id(),
                    "action": {
                        "name": "error",
                        "args": {
                            "error": f"{e}",
                            "original_message_id": message.get("id"),
                        },
                    },
                }
            )

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
                if return_value is not None:
                    self.send(
                        {
                            "to": message["from"],
                            "action": {
                                "name": "response",
                                "args": {
                                    "data": return_value,
                                    "original_message_id": message.get("id"),
                                },
                            },
                        }
                    )
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

    @action
    def response(self, data, original_message_id: str = None):
        """
        Receives a return value from a prior action.

        Args:
            data: The returned value from the action.
            original_message_id: The id field of the original message
        """
        print(
            f"Data was returned from an action. Implement a `response` action to handle it."
        )

    @action
    def error(self, error: str, original_message_id: str = None):
        """
        Receives errors from a prior action.

        Args:
            error: The error message
            original_message_id: The id field of the original message
        """
        print(
            f"An error occurred in an action. Implement an `error` action to handle it."
        )

    def after_add(self):
        """
        Called after the agent is added to a space. Override this method to
        perform any additional setup.
        """

    def before_remove(self):
        """
        Called before the agent is removed from a space. Override this method to
        perform any cleanup.
        """

    def before_action(self, message: dict):
        """
        Called before every action. Override this method for logging or other
        situations where you may want to process all actions.
        """

    def after_action(self, original_message: dict, return_value: str, error: str):
        """
        Called after every action. Override this method for logging or other
        situations where you may want to pass through all actions.
        """

    def request_permission(self, proposed_message: dict) -> bool:
        """
        Implement this method to receive a proposed action message and present
        it to the agent for review. Return true or false to indicate whether
        access should be permitted.
        """
        raise NotImplementedError(
            f"You must implement {self.__class__.__name__}.request_permission to use ACCESS_REQUESTED"
        )
