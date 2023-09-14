import inspect
import re
import threading
import time
import uuid
from typing import Dict, List, Protocol

from docstring_parser import DocstringStyle, parse

from agency.logger import log
from agency.schema import Message


def _python_to_json_type_name(python_type_name: str) -> str:
    return {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'list': 'array',
        'dict': 'object'
    }[python_type_name]


def _generate_help(method: callable) -> dict:
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
            arg_object["type"] = _python_to_json_type_name(
                signature.parameters[arg_name].annotation.__name__)
        elif arg_name in docstring_args and docstring_args[arg_name].type_name is not None:
            arg_object["type"] = _python_to_json_type_name(
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
            help_object["returns"]["type"] = _python_to_json_type_name(
                signature.return_annotation.__name__)
        elif parsed_docstring.returns.type_name is not None:
            help_object["returns"]["type"] = _python_to_json_type_name(
                parsed_docstring.returns.type_name)

        # description
        if parsed_docstring.returns.description is not None:
            help_object["returns"]["description"] = parsed_docstring.returns.description.strip()

    return help_object


# Special action name for responses
_RESPONSE_ACTION_NAME = "[response]"


# Access policies
ACCESS_PERMITTED = "ACCESS_PERMITTED"
ACCESS_DENIED = "ACCESS_DENIED"
ACCESS_REQUESTED = "ACCESS_REQUESTED"


def action(*args, **kwargs):
    """
    Declares instance methods as actions making them accessible to other agents.

    Keyword arguments:
        name: The name of the action. Defaults to the name of the method.
        help: The help object. Defaults to a generated object.
        access_policy: The access policy. Defaults to ACCESS_PERMITTED.
    """
    def decorator(method):
        action_name = kwargs.get("name", method.__name__)
        if action_name == _RESPONSE_ACTION_NAME:
            raise ValueError(f"action name '{action_name}' is reserved")
        method.action_properties = {
            "name": method.__name__,
            "help": _generate_help(method),
            "access_policy": ACCESS_PERMITTED,
            **kwargs}
        return method

    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])  # The decorator was used without parentheses
    else:
        return decorator  # The decorator was used with parentheses


class _QueueProtocol(Protocol):
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


class ActionError(Exception):
    """Raised from the request() method if the action responds with an error"""


class Agent():
    """
    An Actor that may represent an AI agent, computing system, or human user
    """

    def __init__(self,
                 id: str,
                 outbound_queue: _QueueProtocol,
                 receive_own_broadcasts: bool = True):
        """
        Initializes an Agent.

        This constructor is not meant to be called directly. It is invoked by
        the Space class when adding an agent.

        Subclasses should call super().__init__() in their constructor.

        Args:
            id: The id of the agent
            outbound_queue: The outgoing queue for sending messages
            receive_own_broadcasts:
                Whether the agent will receive its own broadcasts. Defaults to
                True
        """
        if len(id) < 1 or len(id) > 255:
            raise ValueError("id must be between 1 and 255 characters")
        if re.match(r"^amq\.", id):
            raise ValueError("id cannot start with \"amq.\"")
        if id == "*":
            raise ValueError("id cannot be \"*\"")
        if outbound_queue is None:
            raise ValueError("outbound_queue must be provided")
        self._id: str = id
        self._outbound_queue: _QueueProtocol = outbound_queue
        self._receive_own_broadcasts: bool = receive_own_broadcasts
        self._is_processing: bool = False  # set by the Space
        self._message_log: List[Message] = []
        self._message_log_lock = threading.Lock()
        self._pending_requests: Dict[str, Message] = {}
        self._pending_requests_lock = threading.Lock()
        self.__thread_local_current_message = threading.local()
        self.__thread_local_current_message.value: Message = None

    def id(self) -> str:
        return self._id

    def send(self, message: dict) -> str:
        """
        Sends (out) a message from this agent.

        Args:
            message: The message

        Returns:
            The id of the sent message
        """
        message["meta"] = {
            "id": uuid.uuid4().__str__(),
            **message.get("meta", {}),
        }
        message["from"] = self.id()
        log("info", f"{self.id()} sending message", message)
        with self._message_log_lock:
            self._message_log.append(message)
        self._outbound_queue.put(message)
        return message["meta"]["id"]

    def request(self, message: dict, timeout: float = 3) -> object:
        """
        Synchronously sends a message then waits for and returns the return
        value of the invoked action.

        This method allows you to call an action synchronously like a function
        and receive its return value in python. If the action raises an
        exception an ActionError will be raised containing the error message.

        Args:
            message: The message to send
            timeout:
                The timeout in seconds to wait for the returned value.
                Defaults to 3 seconds.

        Returns:
            object: The return value of the action.

        Raises:
            TimeoutError: If the timeout is reached
            ActionError: If the action raised an exception
            RuntimeError:
                If called before the agent is processing incoming messages
        """
        if not self._is_processing:
            raise RuntimeError(
                "request() called while agent is not processing incoming messages. Use send() instead.")

        # Send and mark the request as pending
        request_id = self.send(message)
        pending = object()
        with self._pending_requests_lock:
            self._pending_requests[request_id] = pending

        # Wait for response
        start_time = time.time()
        while self._pending_requests[request_id] == pending:
            time.sleep(0.001)
            if time.time() - start_time > timeout:
                raise TimeoutError

        with self._pending_requests_lock:
            response_message = self._pending_requests.pop(request_id)

        # Raise error or return value from response
        if "error" in response_message["action"]["args"]:
            raise ActionError(response_message["action"]["args"]["error"])
        return response_message["action"]["args"]["value"]

    def _receive(self, message: dict):
        """
        Receives and handles an incoming message.

        Args:
            message: The incoming message
        """
        # Ignore own broadcasts if _receive_own_broadcasts is false
        if not self._receive_own_broadcasts \
           and message['from'] == self.id() \
           and message['to'] == '*':
            return

        log("debug", f"{self.id()} received message", message)

        # Record the received message before handling
        with self._message_log_lock:
            self._message_log.append(message)

        # Handle incoming responses
        if message["action"]["name"] == _RESPONSE_ACTION_NAME:
            parent_id = message["meta"]["parent_id"]
            if parent_id in self._pending_requests.keys():
                # This was a response to a request()
                self._pending_requests[parent_id] = message
                # From here the request() method will pick up the response in
                # the existing thread
            else:
                # This was a response to a send()
                if "value" in message["action"]["args"]:
                    handler_callback = self.handle_action_value
                    arg = message["action"]["args"]["value"]
                elif "error" in message["action"]["args"]:
                    handler_callback = self.handle_action_error
                    arg = ActionError(message["action"]["args"]["error"])
                else:
                    raise RuntimeError("Unknown action response")

                # Spawn a thread to handle the response
                def __process_response(arg, current_message):
                    log("debug", f"{self.id()} processing response", message)
                    self.__thread_local_current_message.value = current_message
                    handler_callback(arg)

                threading.Thread(
                    target=__process_response,
                    args=(arg, message, ),
                    daemon=True,
                ).start()

        # Handle all other messages
        else:
            # Spawn a thread to process the message. This means that messages
            # are processed concurrently, but may be processed out of order.
            threading.Thread(
                target=self.__process, args=(message,), daemon=True).start()

    def __process(self, message: dict):
        """
        Top level method within the action processing thread.
        """
        self.__thread_local_current_message.value = message
        message_id = message["meta"]["id"]
        try:
            # Commit the action
            log("debug", f"{self.id()} committing action", message)
            return_value = self.__commit(message)

            # Send the return value
            self.send({
                "meta": {
                    "parent_id": message_id
                },
                "to": message['from'],
                "action": {
                    "name": _RESPONSE_ACTION_NAME,
                    "args": {
                        "value": return_value,
                    }
                }
            })
        except Exception as e:
            # Handle errors (including PermissionError) that occur while
            # committing an action by reporting back to the sender.
            log("warning",
                f"{self.id()} exception while committing action '{message['action']['name']}'", e)
            self.send({
                "meta": {
                    "parent_id": message_id
                },
                "to": message['from'],
                "action": {
                    "name": _RESPONSE_ACTION_NAME,
                    "args": {
                        "error": f"{e.__class__.__name__}: {e}"
                    }
                }
            })

    def __commit(self, message: dict):
        """
        Invokes the action method

        Args:
            message: The incoming message specifying the action

        Raises:
            AttributeError: If the action method is not found
            PermissionError: If the action is not permitted
        """
        try:
            # Check if the action method exists
            action_method = self.__action_method(message["action"]["name"])
        except KeyError:
            # the action was not found
            if message['to'] == '*':
                return  # broadcasts will not raise an error in this situation
            else:
                raise AttributeError(
                    f"\"{message['action']['name']}\" not found on \"{self.id()}\"")

        # Check if the action is permitted
        if not self.__permitted(message):
            raise PermissionError(
                f"\"{self.id()}.{message['action']['name']}\" not permitted")

        self.before_action(message)

        return_value = None
        error = None
        try:
            # Invoke the action method
            return_value = action_method(**message['action'].get('args', {}))
        except Exception as e:
            error = e
            raise
        finally:
            self.after_action(message, return_value, error)
        return return_value

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

    def _find_message(self, message_id: str) -> Message:
        """
        Returns a message from the log with the given ID.

        Args:
            message_id: The ID of the message

        Returns:
            The message or None if not found
        """
        for message in self._message_log:
            if message["meta"]["id"] == message_id:
                return message

    def current_message(self) -> Message:
        """
        Returns the full incoming message which invokes the current action.

        This method may be called within an action or action related callback to
        retrieve the current message, for example to determine the sender or
        inspect other details.

        Returns:
            The current message
        """
        return self.__thread_local_current_message.value

    def parent_message(self, message: Message = None) -> Message:
        """
        Returns the message that the given message is responding to, if any.

        Args:
            message: The message to get the parent message of. Defaults to the
            current message.

        Returns:
            The parent message or None
        """
        if message is None:
            message = self.current_message()
        parent_id = message["meta"].get("parent_id", None)
        if parent_id is not None:
            return self._find_message(parent_id)

    @action
    def help(self, action_name: str = None) -> dict:
        """
        Returns a list of actions on this agent.

        If action_name is passed, returns a list with only that action.
        If no action_name is passed, returns all actions.

        Args:
            action_name: (Optional) The name of an action to request help for

        Returns:
            A dictionary of actions
        """
        special_actions = ["help", _RESPONSE_ACTION_NAME]
        help_list = {
            method.action_properties["name"]: method.action_properties["help"]
            for method in self.__action_methods().values()
            if action_name is None
            and method.action_properties["name"] not in special_actions
            or method.action_properties["name"] == action_name
        }
        return help_list

    def handle_action_value(self, value):
        """
        Receives a return value from a previous action.

        This method receives return values from actions invoked by the send()
        method. It is not called when using the request() method, which returns
        the value directly.

        To inspect the full response message carrying this value, use
        current_message(). To inspect the message which returned the value, use
        parent_message().

        Args:
            value:
                The return value
        """
        if not hasattr(self, "_issued_handle_action_value_warning"):
            self._issued_handle_action_value_warning = True
            log("warning",
                f"A value was returned from an action. Implement {self.__class__.__name__}.handle_action_value() to handle it.")

    def handle_action_error(self, error: ActionError):
        """
        Receives an error from a previous action.

        This method receives errors from actions invoked by the send() method.
        It is not called when using the request() method, which raises an error
        directly.

        To inspect the full response message carrying this error, use
        current_message(). To inspect the message which caused the error, use
        parent_message().

        Args:
            error: The error
        """
        if not hasattr(self, "_issued_handle_action_error_warning"):
            self._issued_handle_action_error_warning = True
            log("warning",
                f"An error was raised from an action. Implement {self.__class__.__name__}.handle_action_error() to handle it.")

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
