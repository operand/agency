import inspect
import re
from typing import List, Protocol

from agency import util
from agency.schema import Message
from agency.util import debug, print_warning

# access keys
ACCESS_PERMITTED = "permitted"
ACCESS_DENIED = "denied"
ACCESS_REQUESTED = "requested"


def action(*args, **kwargs):
    """
    Declares instance methods as actions making them accessible to other agents
    """
    def decorator(method):
        method.action_properties = {
            "name": method.__name__,
            "help": util.generate_help(method),
            "access_policy": ACCESS_PERMITTED,
            **kwargs,
        }
        return method

    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])  # The decorator was used without parentheses
    else:
        return decorator  # The decorator was used with parentheses


class QueueProtocol(Protocol):
    """A protocol for providing an outbound queue for an Agent"""

    def put(self, message: Message):
        """
        Put a message onto the queue for sending

        Args:
            message: The message
        """

    def get(self) -> Message:
        """
        Get the next message from the queue

        Returns:
            The next message

        Raises:
            queue.Empty: If there are no messages
        """


class Agent():
    """
    An Actor that may represent an AI agent, computing system, or human user
    """

    def __init__(self, id: str, outbound_queue: QueueProtocol = None, receive_own_broadcasts: bool = True) -> None:
        """
        Initializes an Agent.

        Args:
            id: The id of the agent
            outqueue: The outgoing queue for sending messages
            receive_own_broadcasts: Whether the agent will receive its own broadcasts. Defaults to True
        """
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError("id cannot start with \"amq.\"")
        if id == "*":
            raise ValueError("id cannot be \"*\"")
        if outbound_queue is None:
            raise ValueError("outqueue must be provided")
        self.__id: str = id
        self._outqueue = outbound_queue
        self._receive_own_broadcasts = receive_own_broadcasts
        # stores all sent and received messages
        self._message_log: List[Message] = []

    def id(self) -> str:
        """
        The id of this agent.
        """
        return self.__id

    def send(self, message: dict):
        """
        Sends (out) a message from this agent.
        """
        message["from"] = self.id()
        self._message_log.append(message)
        self._outqueue.put(message)

    def _receive(self, message: dict):
        """
        Processes an incoming message.
        """
        # debug(f"{self.id()}({id(self)}) received message", message)
        if not self._receive_own_broadcasts \
           and message['from'] == self.id() \
           and message['to'] == '*':
            return

        try:
            # Record message and commit action
            self._message_log.append(message)
            self.__commit(message)
        except Exception as e:
            # Here we handle exceptions that occur while committing an action,
            # including PermissionError's from access denial, by reporting the
            # error back to the sender.
            self.send({
                "to": message['from'],
                "from": self.id(),
                "action": {
                    "name": "error",
                    "args": {
                        "error": f"{e}",
                        "original_message_id": message.get('id'),
                    }
                }
            })

    def __commit(self, message: dict):
        """
        Invokes the action if permitted

        Args:
            message: The message

        Raises:
            PermissionError: If the action is not permitted
        """
        try:
            # Check if the action method exists
            action_method = self.__action_method(message["action"]["name"])
        except KeyError:
            # the action was not found
            if message['to'] == self.id():
                # if it was point to point, raise an error
                raise AttributeError(
                    f"\"{message['action']['name']}\" not found on \"{self.id()}\"")
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
                return_value = action_method(**message['action']['args'])
                self._current_message = None

                # The return value if any, from an action method is sent back to
                # the sender as a "response" action.
                if return_value is not None:
                    self.send({
                        "to": message['from'],
                        "action": {
                            "name": "response",
                            "args": {
                                "data": return_value,
                                "original_message_id": message.get('id'),
                            },
                        }
                    })
            else:
                raise PermissionError(
                  f"\"{self.id()}.{message['action']['name']}\" not permitted")
        except Exception as e:
            error = e  # save the error for after_action
            raise
        finally:
            self.after_action(message, return_value, error)

    def __permitted(self, message: dict) -> bool:
        """
        Checks whether the message's action is allowed
        """
        action_method = self.__action_method(message['action']['name'])
        policy = action_method.action_properties["access_policy"]
        if policy == ACCESS_PERMITTED:
            return True
        elif policy == ACCESS_DENIED:
            return False
        elif policy == ACCESS_REQUESTED:
            return self.request_permission(message)
        else:
            raise Exception(
              f"Invalid access policy for method: {message['action']}, got '{policy}'")

    def __action_methods(self) -> dict:
        instance_methods = inspect.getmembers(self, inspect.ismethod)
        action_methods = {
            method_name: method
            for method_name, method in instance_methods
            if hasattr(method, "action_properties")
        }
        return action_methods

    def __action_method(self, action_name: str):
        """
        Returns the method for the given action name.
        """
        action_methods = self.__action_methods()
        return action_methods[action_name]

    @action
    def help(self, action_name: str = None) -> dict:
        """
        Returns a list of actions on this agent.

        If action_name is passed, returns a list with only that action.
        If no action_name is passed, returns all actions.

        Args:
            action_name: (Optional) The name of an action to request help for

        Returns:
            A list of actions
        """
        special_actions = ["help", "response", "error"]
        help_list = {
            method.action_properties["name"]: method.action_properties["help"]
            for method in self.__action_methods().values()
            if action_name is None
            and method.action_properties["name"] not in special_actions
            or method.action_properties["name"] == action_name
        }
        return help_list

    @action
    def response(self, data, original_message_id: str = None):
        """
        Receives a return value from a prior action.

        Args:
            data: The returned value from the action.
            original_message_id: The id field of the original message
        """
        print_warning(
            f"Data was returned from an action. Implement a `response` action to handle it.")

    @action
    def error(self, error: str, original_message_id: str = None):
        """
        Receives errors from a prior action.

        Args:
            error: The error message
            original_message_id: The id field of the original message
        """
        print_warning(
            f"An error occurred in an action. Implement an `error` action to handle it.")

    def after_add(self):
        """
        Called immediately after the agent is added to a space.

        The agent may send initial messages during this callback, but will not
        begin processing received messages until this callback returns.
        """

    def before_remove(self):
        """
        Called before the agent is removed from a space.

        The agent may send final messages during this callback, but will not
        process any further received messages.
        """

    def before_action(self, message: dict):
        """
        Called before every action.

        This method will only be called if the action exists and is permitted.

        Args:
            message: The received message that contains the action
        """

    def after_action(self, original_message: dict, return_value: str, error: str):
        """
        Called after every action, regardless of whether an error occurred.

        Args:
            original_message: The original message
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
            f"You must implement {self.__class__.__name__}.request_permission to use ACCESS_REQUESTED")
