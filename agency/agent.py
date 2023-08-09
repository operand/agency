import inspect
import re
from typing import List
from docstring_parser import DocstringStyle, parse
from agency import util
from agency.schema import Message
from agency.util import print_warning


# access keys
ACCESS_PERMITTED = "permitted"
ACCESS_DENIED = "denied"
ACCESS_REQUESTED = "requested"


def __generate_help(method: callable) -> dict:
    """
    Generates a help object from a method's docstring and signature

    Args:
        method: the method

    Returns:
        A help object of the form:

        {
            "description": <description>,
            "args": {
                "arg_name": {
                    "type": <type>,
                    "description": <description>
                },
            }
            "returns": {
                "type": <type>,
                "description": <description>
            }
        }
    """
    signature = inspect.signature(method)
    parsed_docstring = parse(method.__doc__, DocstringStyle.GOOGLE)

    help_object = {}

    # description
    if parsed_docstring.short_description is not None:
        description = parsed_docstring.short_description
        if parsed_docstring.long_description is not None:
            description += " " + parsed_docstring.long_description
        help_object["description"] = re.sub(r"\s+", " ", description).strip()

    # args
    help_object["args"] = {}
    docstring_args = {arg.arg_name: arg for arg in parsed_docstring.params}
    arg_names = list(signature.parameters.keys())[1:]  # skip 'self' argument
    for arg_name in arg_names:
        arg_object = {}

        # type
        sig_annotation = signature.parameters[arg_name].annotation
        if sig_annotation is not None and sig_annotation.__name__ != "_empty":
            arg_object["type"] = util.python_to_json_type_name(
                signature.parameters[arg_name].annotation.__name__)
        elif arg_name in docstring_args and docstring_args[arg_name].type_name is not None:
            arg_object["type"] = util.python_to_json_type_name(
                docstring_args[arg_name].type_name)

        # description
        if arg_name in docstring_args and docstring_args[arg_name].description is not None:
            arg_object["description"] = docstring_args[arg_name].description.strip()

        help_object["args"][arg_name] = arg_object

    # returns
    if parsed_docstring.returns is not None:
        help_object["returns"] = {}

        # type
        if signature.return_annotation is not None:
            help_object["returns"]["type"] = util.python_to_json_type_name(
                signature.return_annotation.__name__)
        elif parsed_docstring.returns.type_name is not None:
            help_object["returns"]["type"] = util.python_to_json_type_name(
                parsed_docstring.returns.type_name)

        # description
        if parsed_docstring.returns.description is not None:
            help_object["returns"]["description"] = parsed_docstring.returns.description.strip()

    return help_object


def action(*args, **kwargs):
    def decorator(method):
        method.action_properties = {
            "name": method.__name__,
            "access_policy": ACCESS_PERMITTED,
            "help": __generate_help(method),
            **kwargs,
        }
        return method

    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])  # The decorator was used without parentheses
    else:
        return decorator  # The decorator was used with parentheses


class Agent():
    """
    An Actor that may represent an AI agent, computing system, or human user
    """

    def __init__(self, id: str, receive_own_broadcasts: bool = True) -> None:
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError("id cannot start with \"amq.\"")
        if id == "*":
            raise ValueError("id cannot be \"*\"")
        self.__id: str = id
        self.__receive_own_broadcasts = receive_own_broadcasts
        self._space = None  # set by Space when added
        self._message_log: List[Message] = []  # stores all messages

    def id(self) -> str:
        """
        Returns the id of this agent
        """
        return self.__id

    def send(self, message: dict):
        """
        Sends (out) a message
        """
        message["from"] = self.id()
        self._message_log.append(message)
        self._space._route(message)

    def _receive(self, message: dict):
        """
        Receives and processes an incoming message
        """
        if not self.__receive_own_broadcasts \
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
        Invokes action if permitted otherwise raises PermissionError
        """
        # Check if the action method exists
        try:
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
        Checks whether the action represented by the message is allowed
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
            f"You must implement {self.__class__.__name__}.request_permission to use ACCESS_REQUESTED")
